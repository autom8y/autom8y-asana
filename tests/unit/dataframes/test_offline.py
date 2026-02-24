"""Unit tests for offline DataFrame loader."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.offline import load_project_dataframe


def _make_parquet_bytes(df: pl.DataFrame) -> bytes:
    """Serialize a DataFrame to parquet bytes for mock S3 responses."""
    buf = io.BytesIO()
    df.write_parquet(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Pre-configured mock boto3 S3 client."""
    return MagicMock()


class TestLoadProjectDataframe:
    """Test load_project_dataframe function."""

    def test_missing_bucket_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ASANA_CACHE_S3_BUCKET", raising=False)
        with pytest.raises(ValueError, match="No S3 bucket configured"):
            load_project_dataframe("proj_123")

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_no_parquets_raises(self, mock_boto3: MagicMock) -> None:
        client = MagicMock()
        mock_boto3.client.return_value = client

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [{"Contents": []}]

        with pytest.raises(FileNotFoundError, match="No parquet files found"):
            load_project_dataframe("proj_123", bucket="test-bucket")

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_no_contents_key_raises(self, mock_boto3: MagicMock) -> None:
        """Pages with no Contents key should not crash."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [{}]  # no Contents key

        with pytest.raises(FileNotFoundError, match="No parquet files found"):
            load_project_dataframe("proj_123", bucket="test-bucket")

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_concat_multiple_sections(self, mock_boto3: MagicMock) -> None:
        """Multiple section parquets are concatenated with diagonal_relaxed."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"name": ["A"], "section": ["ACTIVE"], "mrr": [100.0]})
        df2 = pl.DataFrame({"name": ["B"], "section": ["STAGING"], "mrr": [200.0]})

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "dataframes/proj/sections/sec1.parquet"},
                    {"Key": "dataframes/proj/sections/sec2.parquet"},
                ]
            }
        ]

        bytes1 = _make_parquet_bytes(df1)
        bytes2 = _make_parquet_bytes(df2)

        def get_object_side_effect(Bucket: str, Key: str) -> dict:
            body = MagicMock()
            if Key.endswith("sec1.parquet"):
                body.read.return_value = bytes1
            else:
                body.read.return_value = bytes2
            return {"Body": body}

        client.get_object.side_effect = get_object_side_effect

        result = load_project_dataframe("proj", bucket="test-bucket")
        assert len(result) == 2
        assert result["mrr"].sum() == 300.0
        assert set(result["section"].to_list()) == {"ACTIVE", "STAGING"}

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_pagination_across_pages(self, mock_boto3: MagicMock) -> None:
        """Parquet keys are collected across multiple paginator pages."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"val": [1]})
        df2 = pl.DataFrame({"val": [2]})

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "dataframes/p/sections/a.parquet"}]},
            {"Contents": [{"Key": "dataframes/p/sections/b.parquet"}]},
        ]

        bytes1 = _make_parquet_bytes(df1)
        bytes2 = _make_parquet_bytes(df2)

        def get_object_side_effect(Bucket: str, Key: str) -> dict:
            body = MagicMock()
            body.read.return_value = bytes1 if "a.parquet" in Key else bytes2
            return {"Body": body}

        client.get_object.side_effect = get_object_side_effect

        result = load_project_dataframe("p", bucket="test-bucket")
        assert len(result) == 2
        assert result["val"].sum() == 3

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_non_parquet_keys_filtered(self, mock_boto3: MagicMock) -> None:
        """Non-.parquet keys in the listing are skipped."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"val": [42]})

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "dataframes/p/sections/sec1.parquet"},
                    {"Key": "dataframes/p/sections/manifest.json"},
                ]
            }
        ]

        body = MagicMock()
        body.read.return_value = _make_parquet_bytes(df1)
        client.get_object.return_value = {"Body": body}

        result = load_project_dataframe("p", bucket="test-bucket")
        assert len(result) == 1
        assert result["val"].sum() == 42
        # Only 1 get_object call (the .parquet, not .json)
        assert client.get_object.call_count == 1

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_env_var_fallback(self, mock_boto3: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        """Bucket falls back to ASANA_CACHE_S3_BUCKET env var."""
        monkeypatch.setenv("ASANA_CACHE_S3_BUCKET", "env-bucket")

        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"val": [1]})
        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "dataframes/p/sections/s.parquet"}]}
        ]
        body = MagicMock()
        body.read.return_value = _make_parquet_bytes(df1)
        client.get_object.return_value = {"Body": body}

        result = load_project_dataframe("p")
        assert len(result) == 1
        # Verify it used the env var bucket
        client.get_object.assert_called_once_with(
            Bucket="env-bucket", Key="dataframes/p/sections/s.parquet"
        )

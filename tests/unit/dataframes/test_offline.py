"""Unit tests for offline DataFrame loader."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from autom8_asana.dataframes.offline import (
    _list_parquet_keys,
    load_project_dataframe,
    load_project_dataframe_with_meta,
)


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


class TestListParquetKeysMetadata:
    """Test _list_parquet_keys returns LastModified metadata."""

    def test_returns_max_last_modified(self) -> None:
        """_list_parquet_keys should return the max LastModified across all parquets."""
        client = MagicMock()
        paginator = MagicMock()
        client.get_paginator.return_value = paginator

        older = datetime(2026, 2, 20, 12, 0, 0, tzinfo=UTC)
        newer = datetime(2026, 2, 23, 18, 30, 0, tzinfo=UTC)

        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "prefix/sec1.parquet", "LastModified": older},
                    {"Key": "prefix/sec2.parquet", "LastModified": newer},
                ]
            }
        ]

        keys, max_mtime = _list_parquet_keys(client, "bucket", "prefix/")
        assert keys == ["prefix/sec1.parquet", "prefix/sec2.parquet"]
        assert max_mtime == newer

    def test_returns_none_when_no_last_modified(self) -> None:
        """_list_parquet_keys should return None if objects lack LastModified."""
        client = MagicMock()
        paginator = MagicMock()
        client.get_paginator.return_value = paginator

        paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "prefix/sec1.parquet"},
                ]
            }
        ]

        keys, max_mtime = _list_parquet_keys(client, "bucket", "prefix/")
        assert keys == ["prefix/sec1.parquet"]
        assert max_mtime is None

    def test_returns_none_when_empty(self) -> None:
        """_list_parquet_keys returns empty list and None for no results."""
        client = MagicMock()
        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [{"Contents": []}]

        keys, max_mtime = _list_parquet_keys(client, "bucket", "prefix/")
        assert keys == []
        assert max_mtime is None

    def test_max_across_pages(self) -> None:
        """Max LastModified should be computed across paginator pages."""
        client = MagicMock()
        paginator = MagicMock()
        client.get_paginator.return_value = paginator

        t1 = datetime(2026, 2, 20, tzinfo=UTC)
        t2 = datetime(2026, 2, 24, tzinfo=UTC)
        t3 = datetime(2026, 2, 22, tzinfo=UTC)

        paginator.paginate.return_value = [
            {"Contents": [{"Key": "p/a.parquet", "LastModified": t1}]},
            {
                "Contents": [
                    {"Key": "p/b.parquet", "LastModified": t2},
                    {"Key": "p/c.parquet", "LastModified": t3},
                ]
            },
        ]

        keys, max_mtime = _list_parquet_keys(client, "bucket", "p/")
        assert len(keys) == 3
        assert max_mtime == t2


class TestLoadProjectDataframeWithMeta:
    """Test load_project_dataframe_with_meta returns (DataFrame, datetime)."""

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_returns_tuple_with_last_modified(self, mock_boto3: MagicMock) -> None:
        """Should return (DataFrame, max_last_modified) tuple."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"val": [1]})
        mtime = datetime(2026, 2, 23, 12, 0, 0, tzinfo=UTC)

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "dataframes/p/sections/s.parquet", "LastModified": mtime}]}
        ]
        body = MagicMock()
        body.read.return_value = _make_parquet_bytes(df1)
        client.get_object.return_value = {"Body": body}

        df, last_modified = load_project_dataframe_with_meta("p", bucket="test-bucket")
        assert len(df) == 1
        assert last_modified == mtime

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_returns_none_when_no_last_modified(self, mock_boto3: MagicMock) -> None:
        """Should return None for last_modified when S3 objects lack metadata."""
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

        df, last_modified = load_project_dataframe_with_meta("p", bucket="test-bucket")
        assert len(df) == 1
        assert last_modified is None

    @patch("autom8_asana.dataframes.offline.boto3")
    def test_delegates_to_load_project_dataframe(self, mock_boto3: MagicMock) -> None:
        """load_project_dataframe should delegate to load_project_dataframe_with_meta."""
        client = MagicMock()
        mock_boto3.client.return_value = client

        df1 = pl.DataFrame({"val": [42]})
        mtime = datetime(2026, 2, 23, tzinfo=UTC)

        paginator = MagicMock()
        client.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "dataframes/p/sections/s.parquet", "LastModified": mtime}]}
        ]
        body = MagicMock()
        body.read.return_value = _make_parquet_bytes(df1)
        client.get_object.return_value = {"Body": body}

        # load_project_dataframe returns just the DataFrame (drops metadata)
        result = load_project_dataframe("p", bucket="test-bucket")
        assert len(result) == 1
        assert result["val"].sum() == 42

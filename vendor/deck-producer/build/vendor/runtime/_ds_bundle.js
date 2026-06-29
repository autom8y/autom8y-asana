/* @ds-bundle: {"format":3,"namespace":"ContenteDesignSystem_9ed584","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"CardHeader","sourcePath":"components/core/Card.jsx"},{"name":"Callout","sourcePath":"components/feedback/Callout.jsx"},{"name":"Spotlight","sourcePath":"components/feedback/Spotlight.jsx"},{"name":"CopyField","sourcePath":"components/forms/CopyField.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Switch","sourcePath":"components/forms/Switch.jsx"},{"name":"StepHeader","sourcePath":"components/navigation/StepHeader.jsx"},{"name":"StepRow","sourcePath":"components/navigation/StepRow.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"f5f0eb088917","components/core/Button.jsx":"a3add04a5159","components/core/Card.jsx":"261607929711","components/feedback/Callout.jsx":"29de461aa5d0","components/feedback/Spotlight.jsx":"5ba8dbb8da3d","components/forms/CopyField.jsx":"0eafdb97e91d","components/forms/Input.jsx":"b7f3b659a06d","components/forms/Switch.jsx":"6973bee4af1e","components/navigation/StepHeader.jsx":"841fa5d88644","components/navigation/StepRow.jsx":"90c5dc0b2206"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.ContenteDesignSystem_9ed584 = window.ContenteDesignSystem_9ed584 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente badge / pill — eyebrow chips ("Step 01"), status tags,
 * and small labels. Tints map to the semantic palette.
 */
function Badge({
  variant = "tint",
  tone = "blue",
  size = "md",
  uppercase = false,
  children,
  style = {},
  ...rest
}) {
  const tones = {
    blue: {
      solid: ["var(--blue-600)", "#fff"],
      tint: ["var(--blue-100)", "var(--blue-700)"],
      outline: ["transparent", "var(--blue-700)", "var(--blue-200)"]
    },
    navy: {
      solid: ["var(--navy-900)", "#fff"],
      tint: ["#e7ebf4", "var(--navy-900)"],
      outline: ["transparent", "var(--navy-900)", "var(--border-strong)"]
    },
    success: {
      solid: ["var(--success-600)", "#fff"],
      tint: ["var(--success-50)", "var(--success-600)"],
      outline: ["transparent", "var(--success-600)", "var(--success-200)"]
    },
    warning: {
      solid: ["var(--warning-600)", "#fff"],
      tint: ["var(--warning-50)", "var(--warning-600)"],
      outline: ["transparent", "var(--warning-600)", "var(--warning-200)"]
    },
    neutral: {
      solid: ["var(--ink-600)", "#fff"],
      tint: ["var(--mist)", "var(--ink-600)"],
      outline: ["transparent", "var(--ink-600)", "var(--border-default)"]
    }
  };
  const t = (tones[tone] || tones.blue)[variant] || tones.blue.tint;
  const [bg, fg, bd] = t;
  const sizes = {
    sm: {
      padding: "5px 10px",
      font: 11,
      gap: 5
    },
    md: {
      padding: "8px 14px",
      font: 13,
      gap: 6
    },
    lg: {
      padding: "11px 18px",
      font: 14,
      gap: 8
    }
  };
  const s = sizes[size] || sizes.md;
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: s.gap,
      background: bg,
      color: fg,
      border: `1px solid ${bd || "transparent"}`,
      padding: s.padding,
      fontFamily: "var(--font-sans)",
      fontWeight: 700,
      fontSize: s.font,
      lineHeight: 1,
      letterSpacing: uppercase ? "0.12em" : "0",
      textTransform: uppercase ? "uppercase" : "none",
      borderRadius: "var(--radius-pill)",
      whiteSpace: "nowrap",
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente primary button.
 * Calm, confident interactions: hover darkens, press nudges down 1px,
 * focus shows the signature 4px blue halo (never a hard outline).
 */
function Button({
  variant = "primary",
  size = "md",
  iconLeft = null,
  iconRight = null,
  fullWidth = false,
  disabled = false,
  type = "button",
  onClick,
  children,
  style = {},
  ...rest
}) {
  const sizes = {
    sm: {
      height: 40,
      padding: "0 16px",
      font: 15
    },
    md: {
      height: 48,
      padding: "0 22px",
      font: 16
    },
    lg: {
      height: 56,
      padding: "0 30px",
      font: 18
    }
  };
  const s = sizes[size] || sizes.md;
  const variants = {
    primary: {
      background: "var(--blue-600)",
      color: "var(--white)",
      border: "1px solid var(--blue-600)"
    },
    secondary: {
      background: "var(--white)",
      color: "var(--ink-900)",
      border: "1px solid var(--border-default)"
    },
    ghost: {
      background: "transparent",
      color: "var(--blue-600)",
      border: "1px solid transparent"
    },
    dark: {
      background: "var(--navy-900)",
      color: "var(--white)",
      border: "1px solid var(--navy-900)"
    }
  };
  const v = variants[variant] || variants.primary;
  const [hover, setHover] = React.useState(false);
  const [active, setActive] = React.useState(false);
  const hoverStyle = hover && !disabled ? variant === "primary" ? {
    background: "var(--blue-700)",
    borderColor: "var(--blue-700)"
  } : variant === "secondary" ? {
    background: "var(--mist)"
  } : variant === "dark" ? {
    background: "var(--navy-700)",
    borderColor: "var(--navy-700)"
  } : {
    background: "var(--blue-100)"
  } : {};
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setActive(false);
    },
    onMouseDown: () => setActive(true),
    onMouseUp: () => setActive(false),
    style: {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 10,
      width: fullWidth ? "100%" : "auto",
      height: s.height,
      padding: s.padding,
      fontFamily: "var(--font-sans)",
      fontWeight: 700,
      fontSize: s.font,
      lineHeight: 1,
      letterSpacing: "-0.01em",
      borderRadius: "var(--radius-pill)",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      transform: active && !disabled ? "translateY(1px)" : "none",
      boxShadow: variant === "primary" && !disabled ? hover ? "var(--shadow-md)" : "var(--shadow-sm)" : "none",
      transition: "background 120ms var(--ease-standard), transform 120ms var(--ease-standard), box-shadow 200ms var(--ease-standard)",
      ...v,
      ...hoverStyle,
      ...style
    }
  }, rest), iconLeft, children, iconRight);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente content card — white surface, hairline border, soft navy shadow.
 * `elevation` controls the lift; `dark` flips it to a navy section card.
 */
function Card({
  elevation = "md",
  dark = false,
  padding = 28,
  radius = "var(--radius-xl)",
  children,
  style = {},
  ...rest
}) {
  const shadows = {
    none: "none",
    sm: "var(--shadow-sm)",
    md: "var(--shadow-md)",
    lg: "var(--shadow-lg)",
    xl: "var(--shadow-xl)"
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: dark ? "var(--navy-900)" : "var(--surface-card)",
      color: dark ? "var(--white)" : "var(--text-body)",
      border: dark ? "1px solid var(--navy-900)" : "1px solid var(--border-default)",
      borderRadius: radius,
      boxShadow: shadows[elevation] ?? shadows.md,
      padding,
      boxSizing: "border-box",
      ...style
    }
  }, rest), children);
}

/** Optional header row for a Card: eyebrow + title. */
function CardHeader({
  eyebrow,
  title,
  dark = false,
  style = {}
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16,
      ...style
    }
  }, eyebrow && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-sans)",
      fontWeight: 700,
      fontSize: 13,
      letterSpacing: "0.16em",
      textTransform: "uppercase",
      color: dark ? "var(--blue-400)" : "var(--text-eyebrow)"
    }
  }, eyebrow), title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: 24,
      letterSpacing: "-0.01em",
      marginTop: eyebrow ? 8 : 0,
      color: dark ? "var(--white)" : "var(--text-heading)"
    }
  }, title));
}
Object.assign(__ds_scope, { Card, CardHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Callout.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente callout / note — the colored advisory boxes used throughout
 * onboarding: "Pro tip", "Why this matters", "Required pause", etc.
 *
 * `size`: "wizard" (default, byte-for-byte as before) or "slide" (1920×1080 deck
 * scale — larger label + body, padding bumped one coherent step; body ≥24px).
 */
function Callout({
  tone = "success",
  label,
  size = "wizard",
  children,
  style = {},
  ...rest
}) {
  const slide = size === "slide";
  const D = slide ? {
    padding: "22px 26px",
    label: 18,
    body: 24,
    labelMB: 10
  } : {
    padding: "18px 22px",
    label: 13,
    body: 16,
    labelMB: 8
  };
  const tones = {
    success: {
      bg: "var(--success-50)",
      border: "var(--success-200)",
      label: "var(--success-600)"
    },
    warning: {
      bg: "var(--warning-50)",
      border: "var(--warning-200)",
      label: "var(--warning-600)"
    },
    info: {
      bg: "var(--blue-100)",
      border: "var(--blue-200)",
      label: "var(--blue-600)"
    },
    neutral: {
      bg: "var(--mist)",
      border: "var(--border-default)",
      label: "var(--ink-400)"
    }
  };
  const t = tones[tone] || tones.success;
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: t.bg,
      border: `1px solid ${t.border}`,
      borderRadius: "var(--radius-lg)",
      padding: D.padding,
      fontFamily: "var(--font-sans)",
      ...style
    }
  }, rest), label && /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: D.label,
      letterSpacing: "0.14em",
      textTransform: "uppercase",
      color: t.label,
      marginBottom: D.labelMB
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: D.body,
      lineHeight: 1.45,
      color: "var(--ink-900)"
    }
  }, children));
}
Object.assign(__ds_scope, { Callout });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Callout.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Spotlight.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente spotlight — a product screenshot in a floating white frame,
 * with optional highlight halos drawn over the regions to point at.
 * Highlights are positioned in percentages of the image box.
 *
 * Subtractive nested radius: inner frame radius = `calc(radius − pad)`
 * (default 20 − 12 = 8). `size="slide"` keeps that geometry and enlarges only
 * the pill note typography for 1920×1080 legibility; "wizard" (default) is
 * unchanged.
 *
 * Highlight emphasis is two-tier: an informational pointer (`tone:"blue"`, soft
 * ring = "look here") and a critical CLICK target (`tone:"success"`/`"click"`, or
 * `"click-blue"`) — the click tier gets a thicker border, a white separator ring
 * and a stronger glow so the action a viewer must take always out-ranks a mere
 * pointer. Use green click halos sparingly: ideally one per screenshot.
 */
function Spotlight({
  src,
  image,
  alt = "",
  highlights = [],
  pad = 12,
  radius = "var(--radius-xl)",
  elevation = "xl",
  size = "wizard",
  style = {},
  ...rest
}) {
  const slide = size === "slide";
  const shadows = {
    md: "var(--shadow-md)",
    lg: "var(--shadow-lg)",
    xl: "var(--shadow-xl)"
  };
  const imgSrc = src != null ? src : image;
  const noteD = slide ? {
    font: 22,
    pad: "11px 18px",
    top: "calc(100% + 12px)"
  } : {
    font: 14,
    pad: "8px 12px",
    top: "calc(100% + 8px)"
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--border-default)",
      borderRadius: radius,
      boxShadow: shadows[elevation] || shadows.xl,
      padding: pad,
      boxSizing: "border-box",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      position: "relative",
      borderRadius: `calc(${radius} - ${pad}px)`,
      overflow: "hidden",
      border: "1px solid var(--border-subtle)"
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: imgSrc,
    alt: alt,
    style: {
      width: "100%",
      display: "block"
    }
  }), highlights.map((h, i) => {
    // Two emphasis tiers. Informational ("look here") = soft ring.
    // Click ("click this — the critical action") = bolder border, a white
    // separator + stronger glow, and a button-like radius, so it always
    // out-ranks a pointer. `success` is treated as a green click target
    // (its established meaning in these walkthroughs); `click` / `click-blue`
    // are explicit aliases.
    const t = h.tone || "blue";
    const click = t === "success" || t === "click" || t === "click-blue";
    const green = t !== "click-blue" && t !== "blue";
    const bw = click ? slide ? 5 : 4 : slide ? 4 : 3;
    const conf = click ? {
      border: green ? "var(--success-600)" : "var(--blue-600)",
      halo: green ? "var(--halo-click)" : "var(--halo-click-blue)",
      radius: "var(--radius-md)"
    } : {
      border: "var(--blue-600)",
      halo: "var(--halo-blue)",
      radius: "var(--radius-sm)"
    };
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        position: "absolute",
        left: h.left,
        top: h.top,
        width: h.width,
        height: h.height,
        border: `${bw}px solid ${conf.border}`,
        borderRadius: conf.radius,
        boxShadow: conf.halo,
        pointerEvents: "none"
      }
    }, h.note && /*#__PURE__*/React.createElement("div", {
      style: {
        position: "absolute",
        top: noteD.top,
        left: 0,
        background: "var(--navy-900)",
        color: "#fff",
        fontFamily: "var(--font-sans)",
        fontWeight: 700,
        fontSize: noteD.font,
        padding: noteD.pad,
        borderRadius: "var(--radius-pill)",
        whiteSpace: "nowrap",
        boxShadow: "var(--shadow-dark)"
      }
    }, h.note));
  })));
}
Object.assign(__ds_scope, { Spotlight });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Spotlight.jsx", error: String((e && e.message) || e) }); }

// components/forms/CopyField.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente copy-field — an explicitly READ-ONLY value (codes, merge fields,
 * the Contente routing address) on a shaded background, paired with an explicit
 * text "Copy" action. Inner button radius is derived from the container radius
 * minus its padding (absolute nested-radius math).
 *
 * `size`: "wizard" (default, web-app scale, byte-for-byte as before) or "slide"
 * (1920×1080 deck scale — larger value text, taller Copy target, ≥24px floor).
 */
function CopyField({
  value,
  label,
  mono = true,
  size = "wizard",
  pad,
  radius,
  style = {},
  ...rest
}) {
  const slide = size === "slide";
  const P = pad != null ? pad : slide ? 8 : 6;
  const R = radius != null ? radius : slide ? "var(--radius-lg)" : "var(--radius-md)";
  const D = slide ? {
    label: 19,
    value: 26,
    btnH: 56,
    btnFont: 24,
    btnPad: "0 26px",
    labelMB: 10,
    padLeft: 22
  } : {
    label: 15,
    value: 16,
    btnH: 40,
    btnFont: 15,
    btnPad: "0 18px",
    labelMB: 8,
    padLeft: 14
  };
  const [copied, setCopied] = React.useState(false);
  const copy = () => {
    const done = () => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(value).then(done, done);
      } else {
        const ta = document.createElement("textarea");
        ta.value = value;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        done();
      }
    } catch (e) {
      done();
    }
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      fontFamily: "var(--font-sans)",
      ...style
    }
  }, rest), label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontSize: D.label,
      fontWeight: 600,
      color: "var(--ink-900)",
      marginBottom: D.labelMB
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: P,
      background: "var(--mist)",
      /* shaded = read-only */
      border: "1px solid var(--border-default)",
      borderRadius: R,
      padding: P,
      paddingLeft: D.padLeft
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0,
      overflow: "hidden",
      textOverflow: "ellipsis",
      whiteSpace: "nowrap",
      fontFamily: mono ? "var(--font-mono)" : "var(--font-sans)",
      fontWeight: 500,
      fontSize: D.value,
      color: "var(--ink-600)"
    }
  }, value), /*#__PURE__*/React.createElement("button", {
    type: "button",
    onClick: copy,
    style: {
      flex: "none",
      display: "inline-flex",
      alignItems: "center",
      gap: 7,
      height: D.btnH,
      padding: D.btnPad,
      background: copied ? "var(--success-600)" : "var(--blue-600)",
      color: "#fff",
      border: "none",
      borderRadius: `calc(${R} - ${P}px)`,
      /* nested radius math */
      fontFamily: "var(--font-sans)",
      fontWeight: 700,
      fontSize: D.btnFont,
      cursor: "pointer",
      whiteSpace: "nowrap",
      transition: "background 160ms var(--ease-standard)"
    }
  }, copied ? "Copied" : "Copy")));
}
Object.assign(__ds_scope, { CopyField });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/CopyField.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente text input — with optional label, hint and leading/trailing nodes.
 * Focus shows the signature blue halo.
 */
function Input({
  label,
  hint,
  error,
  iconLeft = null,
  iconRight = null,
  mono = false,
  disabled = false,
  style = {},
  containerStyle = {},
  ...rest
}) {
  const [focus, setFocus] = React.useState(false);
  const borderColor = error ? "var(--warning-600)" : focus ? "var(--blue-600)" : "var(--border-default)";
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: "block",
      fontFamily: "var(--font-sans)",
      ...containerStyle
    }
  }, label && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontSize: 15,
      fontWeight: 600,
      color: "var(--ink-900)",
      marginBottom: 8
    }
  }, label), /*#__PURE__*/React.createElement("span", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      background: disabled ? "var(--mist)" : "var(--white)",
      border: `1px solid ${borderColor}`,
      borderRadius: "var(--radius-sm)",
      padding: "0 14px",
      height: 48,
      boxShadow: focus ? "var(--halo-blue)" : "none",
      transition: "border-color 120ms var(--ease-standard), box-shadow 120ms var(--ease-standard)"
    }
  }, iconLeft && /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--ink-400)",
      display: "flex"
    }
  }, iconLeft), /*#__PURE__*/React.createElement("input", _extends({
    disabled: disabled,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      flex: 1,
      border: "none",
      outline: "none",
      background: "transparent",
      fontFamily: mono ? "var(--font-mono)" : "var(--font-sans)",
      fontSize: 16,
      fontWeight: mono ? 500 : 400,
      color: "var(--ink-900)",
      minWidth: 0,
      ...style
    }
  }, rest)), iconRight && /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--ink-400)",
      display: "flex"
    }
  }, iconRight)), (hint || error) && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "block",
      fontSize: 14,
      marginTop: 8,
      color: error ? "var(--warning-600)" : "var(--text-muted)"
    }
  }, error || hint));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/forms/Switch.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente toggle switch — the on/off control for notification settings.
 * Track turns blue when on; knob slides with a calm ease.
 */
function Switch({
  checked = false,
  onChange,
  disabled = false,
  label,
  size = "md",
  style = {},
  ...rest
}) {
  const dims = size === "sm" ? {
    w: 40,
    h: 24,
    k: 18
  } : {
    w: 52,
    h: 30,
    k: 24
  };
  const pad = (dims.h - dims.k) / 2;
  const toggle = () => {
    if (!disabled && onChange) onChange(!checked);
  };
  const control = /*#__PURE__*/React.createElement("span", _extends({
    role: "switch",
    "aria-checked": checked,
    tabIndex: disabled ? -1 : 0,
    onClick: toggle,
    onKeyDown: e => {
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        toggle();
      }
    },
    style: {
      position: "relative",
      display: "inline-block",
      width: dims.w,
      height: dims.h,
      flex: "none",
      borderRadius: "var(--radius-pill)",
      background: checked ? "var(--blue-600)" : "#c5cee0",
      cursor: disabled ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      transition: "background 200ms var(--ease-standard)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      top: pad,
      left: checked ? dims.w - dims.k - pad : pad,
      width: dims.k,
      height: dims.k,
      borderRadius: "50%",
      background: "#fff",
      boxShadow: "0 2px 5px rgba(14,27,57,.35)",
      transition: "left 200ms var(--ease-out)"
    }
  }));
  if (!label) return control;
  return /*#__PURE__*/React.createElement("label", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 12,
      fontFamily: "var(--font-sans)",
      fontSize: 16,
      fontWeight: 600,
      color: "var(--ink-900)",
      cursor: disabled ? "not-allowed" : "pointer"
    }
  }, control, /*#__PURE__*/React.createElement("span", null, label));
}
Object.assign(__ds_scope, { Switch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Switch.jsx", error: String((e && e.message) || e) }); }

// components/navigation/StepHeader.jsx
try { (() => {
/**
 * Contente step header — opens each walkthrough step.
 * Pass `number` to decouple the step number into a dedicated left-hand badge
 * (the scannable index), with the small step label + serif title + lede stacked
 * beside it. Omit `number` for the original stacked-chip layout.
 *
 * `size`:
 *   - "wizard" (default) — web-app scale; renders byte-for-byte as before.
 *   - "slide"  — 1920×1080 deck scale. Bumps type, badge, gap and the badge
 *                radius together as one coherent step (body ≥24px, title ~60px,
 *                serif numeral at display size). Never set individual knobs.
 */
function StepHeader({
  step,
  number = null,
  title,
  children,
  tone = "blue",
  align = "left",
  size = "wizard",
  style = {}
}) {
  const slide = size === "slide";
  const D = slide ? {
    badge: 96,
    badgeRadius: "var(--radius-xl)",
    num: 52,
    gap: 30,
    eyebrow: 20,
    eyebrowLS: "0.16em",
    title: 60,
    body: 28,
    bodyMaxW: 680,
    bodyMT: 20,
    chipPad: "13px 22px",
    chipFont: 18,
    chipLS: "0.14em",
    titleMT: 24,
    padTop: 4,
    eyebrowMB: 12
  } : {
    badge: 66,
    badgeRadius: "var(--radius-lg)",
    num: 32,
    gap: 22,
    eyebrow: 13,
    eyebrowLS: "0.14em",
    title: 38,
    body: 19,
    bodyMaxW: 560,
    bodyMT: 16,
    chipPad: "9px 16px",
    chipFont: 13,
    chipLS: "0.12em",
    titleMT: 18,
    padTop: 2,
    eyebrowMB: 8
  };
  const chip = tone === "key" ? {
    bg: "var(--blue-600)",
    fg: "#fff"
  } : {
    bg: "var(--blue-100)",
    fg: "var(--blue-700)"
  };
  const Title = title ? /*#__PURE__*/React.createElement("h2", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: D.title,
      lineHeight: 1.1,
      letterSpacing: "-0.02em",
      color: "var(--text-heading)",
      margin: 0
    }
  }, title) : null;
  const Body = children ? /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: D.body,
      lineHeight: 1.5,
      color: "var(--text-body)",
      marginTop: D.bodyMT,
      maxWidth: D.bodyMaxW
    }
  }, children) : null;

  // ---- Decoupled left-hand number badge layout ----
  if (number != null) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        display: "flex",
        gap: D.gap,
        alignItems: "flex-start",
        fontFamily: "var(--font-sans)",
        ...style
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: {
        width: D.badge,
        height: D.badge,
        flex: "none",
        borderRadius: D.badgeRadius,
        background: chip.bg,
        color: chip.fg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-display)",
        fontWeight: 700,
        fontSize: D.num,
        lineHeight: 1
      }
    }, number), /*#__PURE__*/React.createElement("div", {
      style: {
        paddingTop: D.padTop
      }
    }, step && /*#__PURE__*/React.createElement("div", {
      style: {
        fontWeight: 700,
        fontSize: D.eyebrow,
        letterSpacing: D.eyebrowLS,
        textTransform: "uppercase",
        color: chip.fg === "#fff" ? "var(--blue-700)" : "var(--text-eyebrow)",
        marginBottom: D.eyebrowMB
      }
    }, step), Title, Body));
  }

  // ---- Original stacked layout ----
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: align,
      fontFamily: "var(--font-sans)",
      ...style
    }
  }, step && /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-block",
      fontWeight: 700,
      fontSize: D.chipFont,
      letterSpacing: D.chipLS,
      textTransform: "uppercase",
      color: chip.fg,
      background: chip.bg,
      padding: D.chipPad,
      borderRadius: "var(--radius-pill)"
    }
  }, step), title && /*#__PURE__*/React.createElement("h2", {
    style: {
      fontFamily: "var(--font-display)",
      fontWeight: 700,
      fontSize: D.title,
      lineHeight: 1.1,
      letterSpacing: "-0.02em",
      color: "var(--text-heading)",
      margin: step ? `${D.titleMT}px 0 0` : 0
    }
  }, title), children && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: D.body,
      lineHeight: 1.5,
      color: "var(--text-body)",
      marginTop: D.bodyMT,
      maxWidth: D.bodyMaxW,
      marginLeft: align === "center" ? "auto" : 0,
      marginRight: align === "center" ? "auto" : 0
    }
  }, children));
}
Object.assign(__ds_scope, { StepHeader });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/StepHeader.jsx", error: String((e && e.message) || e) }); }

// components/navigation/StepRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Contente step row — a single numbered instruction with the number decoupled
 * into a dedicated left-hand badge, so a list of them scans vertically at a glance.
 * Use inside an ordered instruction list; pair several in a flex column with a gap.
 *
 * `size`: "wizard" (default, byte-for-byte as before) or "slide" (1920×1080 deck
 * scale — larger badge + type as one coherent step; body clears the ≥24px floor).
 */
function StepRow({
  n,
  title,
  tone = "navy",
  size = "wizard",
  children,
  style = {},
  ...rest
}) {
  const slide = size === "slide";
  const D = slide ? {
    badge: 56,
    radius: "var(--radius-lg)",
    num: 26,
    gap: 22,
    title: 28,
    body: 25,
    padTop: 2
  } : {
    badge: 38,
    radius: "var(--radius-md)",
    num: 17,
    gap: 16,
    title: 18,
    body: 16.5,
    padTop: 1
  };
  const badge = tone === "blue" ? {
    bg: "var(--blue-600)",
    fg: "#fff"
  } : tone === "tint" ? {
    bg: "var(--blue-100)",
    fg: "var(--blue-700)"
  } : {
    bg: "var(--navy-900)",
    fg: "#fff"
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: "flex",
      gap: D.gap,
      alignItems: "flex-start",
      fontFamily: "var(--font-sans)",
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      width: D.badge,
      height: D.badge,
      flex: "none",
      borderRadius: D.radius,
      background: badge.bg,
      color: badge.fg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontWeight: 700,
      fontSize: D.num,
      lineHeight: 1
    }
  }, n), /*#__PURE__*/React.createElement("div", {
    style: {
      paddingTop: D.padTop
    }
  }, title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      fontSize: D.title,
      color: "var(--ink-900)",
      lineHeight: 1.3
    }
  }, title), children && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: D.body,
      lineHeight: 1.45,
      color: "var(--ink-600)",
      marginTop: title ? slide ? 6 : 4 : 0
    }
  }, children)));
}
Object.assign(__ds_scope, { StepRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/StepRow.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.CardHeader = __ds_scope.CardHeader;

__ds_ns.Callout = __ds_scope.Callout;

__ds_ns.Spotlight = __ds_scope.Spotlight;

__ds_ns.CopyField = __ds_scope.CopyField;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Switch = __ds_scope.Switch;

__ds_ns.StepHeader = __ds_scope.StepHeader;

__ds_ns.StepRow = __ds_scope.StepRow;

})();

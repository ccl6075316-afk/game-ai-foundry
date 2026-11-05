"""Normalize a plan item's root-contact limits; units never affect geometry."""
import math


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + ' must be a finite nonnegative number')
    try:
        value = float(value)
    except (ValueError, OverflowError):
        raise ValueError(name + ' must be a finite nonnegative number') from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be a finite nonnegative number')
    return value


def attachment_limits_cm(spec):
    """Return (outer gap, maximum embedding) in cm.

    Absent attachment_limits retains legacy .10/.60 cm. A declaration must
    contain exactly both mm fields or both cm fields, never mixed units:
    outer_gap_mm/max_embedding_mm or outer_gap_cm/max_embedding_cm.
    """
    if 'attachment_limits' not in spec:
        return .10, .60
    limits = spec['attachment_limits']
    if not isinstance(limits, dict):
        raise ValueError('attachment_limits must be an object')
    for unit, divisor in [('mm', 10), ('cm', 1)]:
        names = ('outer_gap_' + unit, 'max_embedding_' + unit)
        if set(limits) == set(names):
            return tuple(_number(limits[name], 'attachment_limits.' + name) / divisor for name in names)
    raise ValueError('attachment_limits requires both outer_gap_mm/max_embedding_mm or both outer_gap_cm/max_embedding_cm; mixed units, conflicts and unknown fields are invalid')


def root_checker_arguments(spec):
    gap, embedding = attachment_limits_cm(spec)
    return ['--tolerance-cm', str(gap), '--max-penetration-cm', str(embedding)]


def require_report_limits(report, spec):
    """Reject reused or fresh checker results made with different root limits."""
    expected = attachment_limits_cm(spec)
    actual = tuple(_number(report[name], name) for name in ('tolerance_cm', 'max_penetration_cm'))
    if actual != expected:
        raise ValueError('Different root attachment limits: report %r cm, plan %r cm' % (actual, expected))

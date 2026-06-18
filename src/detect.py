# -*- coding: utf-8 -*-
"""
@author: Aidan
@project: MosaicLabAssessment
@filename: detect
"""
from config import GWP_UNDERPERFORMANCE_THRESHOLD, MIN_WEEKS_BELOW_THRESHOLD, HIT_RATE_DROP_THRESHOLD, \
    LOSS_RATIO_MIN_RISE, LOSS_RATIO_TARGET, MIN_WEEKS_ABOVE_PLAN


def detect_gwp_underperformance(premium_df):
    '''
    originally excess_casualty

    Signal 1 — gwp_underperformance:
    actual GWP(revenue) below 60% of plan in at least MIN_WEEKS_BELOW_THRESHOLD, rank by how many weeks it's been below
    '''
    lobs = premium_df["lob"].unique()
    res = []
    for lob in lobs:
        lob_df = premium_df[premium_df["lob"] == lob]
        below_count = (lob_df["actual_gwp"] / lob_df["plan_gwp"] < GWP_UNDERPERFORMANCE_THRESHOLD).sum()
        if below_count >= MIN_WEEKS_BELOW_THRESHOLD:
            res.append({
                "lob": lob,
                "rank": below_count,
                "type": "concern",
                "title": f"{lob}: Structural GWP underperformance",
                "detail": f"Actual GWP was below {GWP_UNDERPERFORMANCE_THRESHOLD:.0%} of plan in {below_count} of {len(lob_df)} weeks.",
                "action": "Check what is underperforming and adjust accordingly"
            })

    return res


def detect_hit_rate_collapse(submission_df):
    '''
    originally cyber_hit_rate

    Signal 2 — hit_rate_collapse:
    average hit rate weeks 1–8 vs weeks 9–12 drops by more than 10pp — sustained collapse, not a one-off. submissions file only
    '''

    lobs = submission_df["lob"].unique()
    res = []
    for lob in lobs:
        lob_df = submission_df[submission_df["lob"] == lob]
        hit_rate = lob_df["bound_count"] / (lob_df["bound_count"] + lob_df["quoted_count"] + lob_df["declined_count"] +
                                            lob_df["ntu_count"])
        early_avg = hit_rate.iloc[:8].mean()
        late_avg = hit_rate.iloc[8:].mean()

        if (early_avg - late_avg) > HIT_RATE_DROP_THRESHOLD:
            res.append({
                "lob": lob,
                "rank": early_avg - late_avg,
                "type": "concern",
                "title": "Hit rate collapse in weeks 9–12",
                "detail": f"Hit rate averaged {early_avg:.0%} in weeks 1–8, dropping to {late_avg:.0%} in weeks 9–12.",
                "action": "Review pricing against market — rising NTU suggests competitors are offering cheaper terms."
            })
    return res


def detect_loss_ratio_trend(loss_df):
    '''
    originally environmental_loss_ratio

    Signal 3 — loss_ratio_trend:
    latest YTD loss ratio exceeds week-1 value by more than 10pp and is above the 60% target — direction matters as much as level. → loss file only
    '''
    lobs = loss_df["lob"].unique()
    res = []
    for lob in lobs:
        lob_df = loss_df[loss_df["lob"] == lob]
        latest_loss_ratio = lob_df["attritional_loss_ratio_ytd"].iloc[-1]
        week1_loss_ratio = lob_df["attritional_loss_ratio_ytd"].iloc[0]
        is_rise_exceeds = latest_loss_ratio - week1_loss_ratio > LOSS_RATIO_MIN_RISE
        is_latest_value_above = latest_loss_ratio > LOSS_RATIO_TARGET

        if is_rise_exceeds and is_latest_value_above:
            res.append({
                "lob": lob,
                "rank": latest_loss_ratio - week1_loss_ratio,
                "type": "concern",
                "title": "Loss ratio deteriorating above target",
                "detail": f"Attritional loss ratio has risen from {week1_loss_ratio:.0%} at week 1 to {latest_loss_ratio:.0%} at week 12 — {latest_loss_ratio - week1_loss_ratio:.0%} above starting point and beyond the 60% target.",
                "action": "Flag for claims review and assess whether recent bound business warrants a rate adequacy check."
            })
    return res


def detect_political_violence(premium_df, loss_df):
    '''
    Political Violence:
    GWP beats plan in at least 8 of 12 weeks and loss ratio stays below 60% — growth is only an opportunity if it's profitable. → premium and loss files combined
    '''
    political_violence_premium = premium_df[premium_df["lob"] == "Political Violence"]
    beating_plan_count = (
            political_violence_premium["actual_gwp"] / political_violence_premium["plan_gwp"] >= 1.0).sum()

    political_violence_loss = loss_df[loss_df["lob"] == "Political Violence"]
    latest_loss_ratio = political_violence_loss["attritional_loss_ratio_ytd"].iloc[-1]

    if beating_plan_count >= MIN_WEEKS_ABOVE_PLAN and latest_loss_ratio < LOSS_RATIO_TARGET:
        return {
            "lob": "Political Violence",
            "type": "opportunity",
            "title": "Political Violence: Consistent outperformance with healthy loss ratio",
            "detail": f"GWP exceeded plan in {beating_plan_count} of {len(political_violence_premium)} weeks. Loss ratio stands at {latest_loss_ratio:.0%} — well below the 60% target. Growth is profitable.",
            "action": "Assess capacity headroom. If the book can absorb more volume at current margins, consider increasing the plan allocation."
        }
    return None


def detect_all(premium_df, submission_df, loss_df):
    signal1 = detect_excess_casualty(premium_df)
    signal2 = detect_cyber_hit_rate(submission_df)
    signal3 = detect_environmental_loss(loss_df)
    signal4 = detect_political_violence(premium_df, loss_df)
    return [s for s in [signal1, signal2, signal3, signal4] if s is not None]

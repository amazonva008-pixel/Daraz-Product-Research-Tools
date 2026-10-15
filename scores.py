from itertools import accumulate


def normalize(value, min_val, max_val, invert=False):
    if min_val == max_val:
        return 50

    else:
        raw_score = (value - min_val)/(max_val- min_val) * 100
        if invert:
            return (100 - raw_score)
        else:
            return raw_score








def calculate_opportunity_score(scores: dict[str, float], weights: dict[str, float]):
    """
       calculates opportunity scores by checking score and weights of different angles of
       market aspects

       Args:
           scores: it is based on how good the market is 100 being the best and 0 being the lowest
           weights: it decides the impact of each aspect such as competition or demand on opportunity of market
            weights get auto normalized
       Returns:
           It gives a Score of each keyword based on the scores and weights of the market aspects
       """
    total = 0
    if not scores:
        return None
    elif scores.keys() == weights.keys():
        usable_weights = {}

        for key in weights:
            if scores[key] is not None:
                usable_weights[key] = weights[key]

        sum_of_weights = sum(usable_weights.values())
        adjusted_weights = {}
        for key in usable_weights:
            adjusted_weights[key] = usable_weights[key] / sum_of_weights

        breakdown = {}
        for kw in usable_weights:
            score = scores[kw]
            weight = adjusted_weights[kw]
            breakdown[kw] = score * weight
            total = total + score * weight


    else:
       return None

    return {"total": total, "breakdown": breakdown}






def normalize_dict(scores: dict[str, float], invert=False):
    """
    normalizing the count of seller count, review count etc against the other keywords in the same niche
    Args:
     scores: it is a dictionary with keyword name and a value in front, the value could be
    review median, review count, seller count etc
    return: it returns a normalized number comparable to other keywords in the niche helping to rank the
    keywords
    """
    numbers = [value for value in scores.values() if value is not None]
    if not numbers:
        return {key: None for key in scores}
    min_val = min(numbers)
    max_val = max(numbers)
    normalized_value = {}
    for key in scores:
        single_value = scores[key]
        if single_value is None:
            normalized_value[key] = None
        else:
            normalized_value[key] = normalize(single_value, min_val, max_val, invert)

    return normalized_value


def normalize_all_signals(all_signals):
    normalized_signals = {}
    INVERT_RULES = {
        "median_reviews": True,  # fewer reviews on top listings = more opportunity
        "median_rating": True,
        "median_sold": False,  # more sales = more demand
        "median_price": False,  # neutral/context, but let's say higher isn't "bad" by default
        "dominance": True,  # more dominant leader = worse for a new seller
        "sale_to_review": False,  # ambiguous, but let's not invert for now
        "total_listings": True,  # more listings = more saturated/competitive,


    }
    for signal_name in all_signals:
        raw_dict = all_signals[signal_name]
        invert = INVERT_RULES[signal_name]
        normalized_signals[signal_name] = normalize_dict(raw_dict, invert=invert)
    return normalized_signals



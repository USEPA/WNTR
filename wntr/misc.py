def timedelta_to_sec(self, timedelta):
    """
    Converts timedelta to seconds.

    Parameters
    ----------
    timedelta : Pandas tmedelta object.

    Returns
    -------
    seconds as integer
    """

    return int(timedelta.components.days*24*60*60 + timedelta.components.hours*60*60 + timedelta.components.minutes*60 + timedelta.components.seconds)



def lst(df):
    points_per_rank = [20, 17, 14, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2] + [1] * 100
    rank = df.query('status=="OK"') \
        .groupby(['garaname', 'classname'])['time'] \
        .rank(method='min', ascending=True) \
        .astype(int)
    out = rank.apply(lambda x: points_per_rank[x - 1]).astype(int)
    return out


def tl(df):
    default_pv = 100
    pv = {
        'M12': 40,
        'W12': 40,
        'M35': 80,
        'W35': 80,
        'M45': 80,
        'W45': 80,
        'M55': 80,
        'W55': 80,
        'M65': 80,
        'W65': 80,
    }
    winner_times = df.query('status=="OK"').groupby(['garaname', 'classname'])['time'].min()

    def points_func(x):
        if x['status'] == "OK":
            _pv = pv.get(x['classname'], default_pv)
            _wt = winner_times[x['garaname']][x['classname']]
            _t = x['time']
            return _pv * ((_wt / _t)**2)
        else:
            return 0
    out = df.apply(points_func, axis=1)
    return out
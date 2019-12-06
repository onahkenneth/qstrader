import datetime
import json

import numpy as np

import qstrader.statistics.performance as perf


class JSONStatistics(object):
    """
    Standalone class to output basic backtesting statistics
    into a JSON file format.

    Parameters
    ----------
    equity_curve : `pd.DataFrame`
        The equity curve DataFrame indexed by date-time.
    benchmark_curve : `pd.DataFrame`, optional
        The (optional) equity curve DataFrame for the benchmark
        indexed by time.
    periods : `int`, optional
        The number of periods to use for Sharpe ratio calculation.
    output_filename : `str`
        The filename to output the JSON statistics dictionary to.
    """

    def __init__(
        self,
        equity_curve,
        benchmark_curve=None,
        periods=252,
        output_filename='statistics.json'
    ):
        self.equity_curve = equity_curve
        self.benchmark_curve = benchmark_curve
        self.periods = periods
        self.output_filename = output_filename
        self.statistics = self._create_full_statistics()

    @staticmethod
    def _series_to_tuple_list(series):
        """
        Converts Pandas Series indexed by date-time into
        list of tuples indexed by milliseconds since epoch.

        Parameters
        ----------
        series : `pd.Series`
            The Pandas Series to be converted.

        Returns
        -------
        `list[tuple]`
            The list of epoch-indexed tuple values.
        """
        return [
            (
                int(
                    datetime.datetime.combine(
                        k, datetime.datetime.min.time()
                    ).timestamp() * 1000.0
                ), v
            )
            for k, v in series.to_dict().items()
        ]

    @staticmethod
    def _calculate_returns(curve):
        """
        Appends returns and cumulative returns to the supplied equity
        curve DataFrame.

        Parameters
        ----------
        curve : `pd.DataFrame`
            The equity curve DataFrame.
        """
        curve['Returns'] = curve['Equity'].pct_change().fillna(0.0)
        curve['CumReturns'] = np.exp(np.log(1 + curve['Returns']).cumsum())

    def _calculate_statistics(self, curve):
        """
        Creates a dictionary of various statistics associated with
        the backtest of a trading strategy via a supplied equity curve.

        All Pandas Series indexed by date-time are converted into
        milliseconds since epoch representation.

        Parameters
        ----------
        curve : `pd.DataFrame`
            The equity curve DataFrame.

        Returns
        -------
        `dict`
            The statistics dictionary.
        """
        stats = {}

        # Drawdown, max drawdown, max drawdown duration
        dd_s, max_dd, dd_dur = perf.create_drawdowns(curve['CumReturns'])

        # Equity curve and returns
        stats['equity_curve'] = JSONStatistics._series_to_tuple_list(curve['Equity'])
        stats['returns'] = JSONStatistics._series_to_tuple_list(curve['Returns'])
        stats['cum_returns'] = JSONStatistics._series_to_tuple_list(curve['CumReturns'])

        # Drawdown statistics
        stats['drawdowns'] = JSONStatistics._series_to_tuple_list(dd_s)
        stats['max_drawdown'] = max_dd
        stats['max_drawdown_duration'] = dd_dur

        # Performance
        stats['cagr'] = perf.create_cagr(curve['CumReturns'], self.periods)
        stats['annualised_vol'] = curve['Returns'].std() * np.sqrt(self.periods)
        stats['sharpe'] = perf.create_sharpe_ratio(curve['Returns'], self.periods)
        stats['sortino'] = perf.create_sortino_ratio(curve['Returns'], self.periods)

        return stats

    def _create_full_statistics(self):
        """
        Create the 'full' statistics dictionary, which has an entry for the
        strategy and an optional entry for any supplied benchmark.

        Returns
        -------
        `dict`
            The strategy and (optional) benchmark statistics dictionary.
        """
        full_stats = {}

        JSONStatistics._calculate_returns(self.equity_curve)
        full_stats['strategy'] = self._calculate_statistics(self.equity_curve)

        if self.benchmark_curve is not None:
            JSONStatistics._calculate_returns(self.benchmark_curve)
            full_stats['benchmark'] = self._calculate_statistics(self.benchmark_curve)

        return full_stats

    def to_file(self):
        """
        Outputs the statistics dictionary to a JSON file.
        """
        with open(self.output_filename, 'w') as outfile:
            json.dump(self.statistics, outfile)

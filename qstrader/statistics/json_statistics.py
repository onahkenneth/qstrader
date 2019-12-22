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
    strategy_id : `str`, optional
        The optional ID string for the strategy to pass to
        the statistics dict.
    strategy_name : `str`, optional
        The optional name string for the strategy to pass to
        the statistics dict.
    benchmark_curve : `pd.DataFrame`, optional
        The (optional) equity curve DataFrame for the benchmark
        indexed by time.
    benchmark_id : `str`, optional
        The optional ID string for the benchmark to pass to
        the statistics dict.
    benchmark_name : `str`, optional
        The optional name string for the benchmark to pass to
        the statistics dict.
    periods : `int`, optional
        The number of periods to use for Sharpe ratio calculation.
    output_filename : `str`
        The filename to output the JSON statistics dictionary to.
    """

    def __init__(
        self,
        equity_curve,
        target_allocations,
        strategy_id=None,
        strategy_name=None,
        benchmark_curve=None,
        benchmark_id=None,
        benchmark_name=None,
        periods=252,
        output_filename='statistics.json'
    ):
        self.equity_curve = equity_curve
        self.target_allocations = target_allocations
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.benchmark_curve = benchmark_curve
        self.benchmark_id = benchmark_id
        self.benchmark_name = benchmark_name
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
    def _dataframe_to_column_list(df):
        """
        Converts Pandas DataFrame indexed by date-time into
        list of tuples indexed by milliseconds since epoch.

        Parameters
        ----------
        df : `pd.DataFrame`
            The Pandas DataFrame to be converted.

        Returns
        -------
        `list[tuple]`
            The list of epoch-indexed tuple values.
        """
        col_list = []
        for k, v in df.to_dict().items():
            name = k.replace('EQ:', '')
            date_val_tups = [
                (
                    int(
                        datetime.datetime.combine(
                            date_key, datetime.datetime.min.time()
                        ).timestamp() * 1000.0
                    ), date_val
                )
                for date_key, date_val in v.items()
            ]
            col_list.append({'name': name, 'data': date_val_tups})
        return col_list

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

    def _calculate_allocations(self, allocations):
        """
        """
        return JSONStatistics._dataframe_to_column_list(allocations)

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
        full_stats['strategy']['target_allocations'] = self._calculate_allocations(
            self.target_allocations
        )

        if self.benchmark_curve is not None:
            JSONStatistics._calculate_returns(self.benchmark_curve)
            full_stats['benchmark'] = self._calculate_statistics(self.benchmark_curve)

        if self.strategy_id is not None:
            full_stats['strategy_id'] = self.strategy_id
        if self.strategy_name is not None:
            full_stats['strategy_name'] = self.strategy_name
        if self.benchmark_id is not None:
            full_stats['benchmark_id'] = self.benchmark_id
        if self.benchmark_name is not None:
            full_stats['benchmark_name'] = self.benchmark_name

        return full_stats

    def to_file(self):
        """
        Outputs the statistics dictionary to a JSON file.
        """
        with open(self.output_filename, 'w') as outfile:
            json.dump(self.statistics, outfile)

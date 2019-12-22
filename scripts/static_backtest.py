import sys

import click
import pandas as pd
import pytz

from qstrader.alpha_model.fixed_signals import FixedSignalsAlphaModel
from qstrader.statistics.json_statistics import JSONStatistics
from qstrader.statistics.tearsheet import TearsheetStatistics
from qstrader.trading.backtest import BacktestTradingSession


def obtain_allocations(allocations):
    """
    Converts the provided command-line allocations string
    into a dictionary used for QSTrader.

    Parameters
    ----------
    allocations : `str`
        The asset allocations string.

    Returns
    -------
    `dict`
        The asset allocation dictionary
    """
    allocs_dict = {}
    try:
        allocs = allocations.split(',')
        for alloc in allocs:
            alloc_asset, alloc_value = alloc.split(':')
            allocs_dict['EQ:%s' % alloc_asset] = float(alloc_value)
    except Exception:
        print(
            "Could not determine the allocations from the provided "
            "allocations string. Terminating."
        )
        sys.exit()
    else:
        return allocs_dict


@click.command()
@click.option('--start-date', 'start_date', help='Backtest starting date')
@click.option('--end-date', 'end_date', help='Backtest ending date')
@click.option('--allocations', 'allocations', help='Allocations key-values, i.e. "SPY:0.6,AGG:0.4"')
@click.option('--title', 'strat_title', help='Backtest strategy title')
@click.option('--id', 'strat_id', help='Backtest strategy ID string')
def cli(start_date, end_date, allocations, strat_title, strat_id):
    start_dt = pd.Timestamp('%s 00:00:00' % start_date, tz=pytz.UTC)
    end_dt = pd.Timestamp('%s 23:59:00' % end_date, tz=pytz.UTC)

    alloc_dict = obtain_allocations(allocations)

    strategy_assets = alloc_dict.keys()
    strategy_alpha_model = FixedSignalsAlphaModel(alloc_dict)
    strategy_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        strategy_assets,
        strategy_alpha_model,
        rebalance='end_of_month',
        account_name=strat_title,
        portfolio_id='STATIC001',
        portfolio_name=strat_title,
        cash_buffer_percentage=0.01
    )
    strategy_backtest.run()

    # Benchmark: 60/40 US Equities/Bonds
    benchmark_assets = ['EQ:SPY', 'EQ:AGG']
    benchmark_signal_weights = {'EQ:SPY': 0.6, 'EQ:AGG': 0.4}
    benchmark_title = '60/40 US Equities/Bonds'
    benchmark_alpha_model = FixedSignalsAlphaModel(benchmark_signal_weights)
    benchmark_backtest = BacktestTradingSession(
        start_dt,
        end_dt,
        benchmark_assets,
        benchmark_alpha_model,
        rebalance='end_of_month',
        account_name='60/40 US Equities/Bonds',
        portfolio_id='6040EQBD',
        portfolio_name=benchmark_title,
        cash_buffer_percentage=0.01
    )
    benchmark_backtest.run()

    output_filename = ('%s_monthly.json' % strat_id).replace('-', '_')
    stats = JSONStatistics(
        equity_curve=strategy_backtest.get_equity_curve(),
        target_allocations=strategy_backtest.get_target_allocations(),
        strategy_id=strat_id,
        strategy_name=strat_title,
        benchmark_curve=benchmark_backtest.get_equity_curve(),
        benchmark_id='6040-us-equitiesbonds',
        benchmark_name=benchmark_title,
        output_filename=output_filename
    )
    stats.to_file()

    # Performance Output
    tearsheet = TearsheetStatistics(
        strategy_equity=strategy_backtest.get_equity_curve(),
        benchmark_equity=benchmark_backtest.get_equity_curve(),
        title=strat_title
    )
    tearsheet.plot_results()


if __name__ == "__main__":
    cli()

__author__ = 'sdegryze'

from mint.api import MintConnection, Portfolio
from mint.sendemail import sendemail
import resources
import os

def show_info():
    os.chdir(os.path.dirname(__file__))
    mc = MintConnection(resources.mint_username, resources.mint_password)

    investment_account_ids = mc.get_investment_account_Ids()

    my_portfolio = Portfolio()

    for investment_account_id in investment_account_ids:
        my_portfolio.add_holdings(mc.get_holdings(investment_account_id))
    my_portfolio.consolidate_holdings()
    my_portfolio.last_updated = mc.reported_last_date

    result_msg = []
    result_msg.append( "As of %s, your portfolio's total value is $%.2f" %\
          (mc.reported_last_date, my_portfolio.total_value()))
    result_msg.append("")

    symbols = my_portfolio.get_symbols()
    asset_value = my_portfolio.value_by_symbol()

    result_msg.append("%-5s%9s" % ("ticker", "value"))
    for idx, symbol in enumerate(symbols):
        result_msg.append("%-5s%10.2f" % (symbol, asset_value[symbol]))
    result_msg.append("")

    assets = Portfolio.asset_allocation_model.keys()
    value_by_asset = my_portfolio.value_by_asset()
    percentage_by_asset = my_portfolio.percentage_by_asset()
    ideal_allocation = {k: v["fraction"] for (k, v) in Portfolio.asset_allocation_model.items()}

    result_msg.append("%-25s%10s%10s%10s" % ("asset", "value", "fraction", "goal"))
    for idx, asset in enumerate(assets):
        result_msg.append("%-25s%10.2f%10.2f%10.2f" %\
              (asset, value_by_asset[asset], percentage_by_asset[asset], ideal_allocation[asset]))
    result_msg.append("")
    result_msg.extend(my_portfolio.rebalance_portfolio())
    result_msg = "\n".join(result_msg)

    sendemail(result_msg,
              resources.from_addr,
              resources.to_addr,
              resources.email_username,
              resources.email_password)

    my_portfolio.write_to_log()

if __name__=="__main__":
    show_info()
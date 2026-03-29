def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, 
                             open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    g.stock_num = 10
    run_monthly(trade, 1, time='open')

def trade(context):
    q = query(valuation.code, valuation.pe_ratio
        ).filter(valuation.pe_ratio > 0
        ).order_by(valuation.pe_ratio.asc())
    df = get_fundamentals(q)
    
    buylist = list(df['code'][:g.stock_num])
    
    current_data = get_current_data()
    buylist = [stock for stock in buylist 
               if not current_data[stock].paused 
               and not current_data[stock].is_st]
    
    for stock in context.portfolio.positions:
        if stock not in buylist:
            order_target(stock, 0)
    
    if len(buylist) > 0:
        weight = 1.0 / len(buylist)
        for stock in buylist:
            target_value = context.portfolio.total_value * weight
            order_target_value(stock, target_value)
def initialize(context):
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True) 
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, 
                             open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    
    g.stock_num = 10           
    g.factor_weights = {       
        'pe': 0.4,             # 市盈率
        'roe': 0.4,            # 净资产收益率
        'mom': 0.2             # 动量
    }
    run_monthly(trade, 1, time='open')

def trade(context):
    # 获取PE和ROE
    q = query(valuation.code, 
              valuation.pe_ratio,
              indicator.roe         
        ).filter(valuation.pe_ratio > 0,
                 indicator.roe != None)
    df = get_fundamentals(q)
    
    if df.empty:
        return
    
    df.rename(columns={'pe_ratio': 'pe', 'roe': 'roe'}, inplace=True)
    
    # 计算动量（过去20日收益率）
    momentum = {}
    for stock in df['code'].tolist():
        try:
            prices = get_price(stock, count=21, frequency='daily', fields=['close'])
            if len(prices) >= 20:
                mom = (prices['close'][-2] - prices['close'][0]) / prices['close'][0]
                momentum[stock] = mom
            else:
                momentum[stock] = 0
        except:
            momentum[stock] = 0
    df['momentum'] = df['code'].map(momentum)
    
    df = df.dropna(subset=['momentum'])
    
    # 因子排名与标准化
    df['pe_rank'] = df['pe'].rank(ascending=True)
    df['roe_rank'] = df['roe'].rank(ascending=False)
    df['mom_rank'] = df['momentum'].rank(ascending=False)
    
    max_rank = len(df)
    df['pe_score'] = 1 - (df['pe_rank'] / max_rank)
    df['roe_score'] = 1 - (df['roe_rank'] / max_rank)
    df['mom_score'] = 1 - (df['mom_rank'] / max_rank)
    
    # 综合得分
    df['total_score'] = (df['pe_score'] * g.factor_weights['pe'] + 
                         df['roe_score'] * g.factor_weights['roe'] + 
                         df['mom_score'] * g.factor_weights['mom'])
    
    #选股
    df = df.sort_values('total_score', ascending=False)
    buylist = list(df['code'][:g.stock_num])
    
    #风控
    current_data = get_current_data()
    buylist = [stock for stock in buylist 
               if not current_data[stock].paused 
               and not current_data[stock].is_st]
    
    if not buylist:
        return
    
    
    # 卖出不在buylist的持仓
    for stock in context.portfolio.positions:
        if stock not in buylist:
            order_target(stock, 0)
    
    weight = 1.0 / len(buylist)
    for stock in buylist:
        target_value = context.portfolio.total_value * weight
        order_target_value(stock, target_value)
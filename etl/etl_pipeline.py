import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json

def extract_transform_data():
    tables = {'campaigns': pd.read_csv('campaigns.csv'), 
            'events' : pd.read_csv('events.csv'),
            'order_items' : pd.read_csv('order_items.csv'),
            'orders' : pd.read_csv('orders.csv'),
            'sessions' : pd.read_csv('sessions.csv'),
            'users' : pd.read_csv('users.csv'),
            'products' : pd.read_json('products.json')}

    for name, df in tables.items():
        # 1. Handling duplicates:
        count_of_duplicates = df.duplicated().sum()
        df = df.drop_duplicates()
        # 2. Handling inconsistent casing and values
        df.columns = df.columns.str.strip().str.lower()
        cat_cols = df.select_dtypes(include=['object', 'str']).columns
        for col in cat_cols:
            df[col] = df[col].astype(str).str.strip().str.lower()
        # 3. Standardising date-time columns
        date_cols= [col for col in df.columns if 'ts' in col or 'date' in col]
        for d_col in date_cols:
            df[d_col] = pd.to_datetime(df[d_col], errors= 'coerce')
        # Update the dictionary
        tables[name] = df
        
        # 4. handling null values:
        # Translates to: "In the sessions table, WHERE variant is A or B, SET device to 'web'"
        tables['sessions'].loc[tables['sessions']['variant'].isin(['a', 'b']), 'device'] = 'web'
        tables['orders']['user_id'] = tables['orders']['user_id'].fillna('Guest')
        tables['sessions']= tables['sessions'].fillna({'user_id': 'guest', 'device' : 'unknown', 'variant': 'not-eligible'})

        print(f'Table: {name:12} | Duplicates Removed: {count_of_duplicates:<4} | Nulls: {df.isnull().sum().sum()} | Shape: {df.shape} ')
    return tables

def handling_outliers(data_dict):
    """
    Step 2: Implement the Cap + Flag logic for Revenue metrics.
    Uses 1.5 * IQR to define the ceiling.
    """
    revenue_cols = ['net_amount', 'gross_amount', 'discount_amount']
    orders = data_dict['orders'].copy()
    # 1. Calculate IQR and Limits per column
    Q1 = orders[revenue_cols].quantile(0.25)
    Q3 = orders[revenue_cols].quantile(0.75)
    IQR = Q3 - Q1
    # Define specific ceilings for each column
    upper_limits = Q3 + 1.5 * IQR
    lower_limits = Q1 - 1.5 * IQR
    # 2. Add the FLAG (For auditing)
    orders['is_outlier'] = (orders[revenue_cols] > upper_limits).any(axis=1) | \
                        (orders[revenue_cols] < lower_limits).any(axis=1)
    # 3. OVERWRITE the original columns with the capped values
    # We use a loop to ensure each column is capped by its OWN specific limit
    for col in revenue_cols:
        orders[col] = orders[col].clip(lower=lower_limits[col], upper=upper_limits[col])
    # 4. Save back to the main data structure
    data_dict['orders'] = orders

    return data_dict

def create_fact_sessions(data_dict):
    """
    Output 1: fact_sessions.csv (1 row per session)
    Includes Funnel Flags, Timing Metrics, and Session Metadata.
    """
    sessions = data_dict['sessions'].copy()
    events = data_dict['events'].copy()
    orders = data_dict['orders'].copy()
    
    # 1. EVENT TIMINGS
    # We group by session and event type to find the FIRST time each action happened
    first_events = events.groupby(['session_id', 'event_type'])['event_ts'].min().unstack()
    
    # 2. MERGE BASE DATA
    fact_sessions = pd.merge(sessions, first_events, on='session_id', how='left')

    # 3. DERIVED FIELDS (Seconds)
    fact_sessions['time_to_cart_sec'] = (fact_sessions['add_to_cart'] - fact_sessions['session_start_ts']).dt.total_seconds()
    fact_sessions['time_to_checkout_sec'] = (fact_sessions['begin_checkout'] - fact_sessions['session_start_ts']).dt.total_seconds()
    fact_sessions['time_to_purchase_sec'] = (fact_sessions['purchase'] - fact_sessions['session_start_ts']).dt.total_seconds()
    fact_sessions['time_to_payment_sec'] = (fact_sessions['payment_attempt'] - fact_sessions['session_start_ts']).dt.total_seconds()
    # 4. FUNNEL FLAGS
    fact_sessions['has_product_view'] = fact_sessions['product_view'].notnull().astype(int)
    fact_sessions['has_add_to_cart'] = fact_sessions['add_to_cart'].notnull().astype(int)
    fact_sessions['has_begin_checkout'] = fact_sessions['begin_checkout'].notnull().astype(int)
    fact_sessions['has_payment_attempt'] = fact_sessions['payment_attempt'].notnull().astype(int)
    fact_sessions['has_purchase'] = fact_sessions['purchase'].notnull().astype(int)

    # 5. SESSION DURATION (Synced logic)
    last_event = events.groupby('session_id')['event_ts'].max().rename('last_event_ts')
    fact_sessions = pd.merge(fact_sessions, last_event, on='session_id', how='left')
    
    fact_sessions['session_duration_sec'] = (fact_sessions['last_event_ts'] - fact_sessions['session_start_ts']).dt.total_seconds()
    
    # Ensure duration covers the purchase time
    duration_cols = ['session_duration_sec', 'time_to_cart_sec', 'time_to_checkout_sec', 'time_to_purchase_sec']
    fact_sessions['session_duration_sec'] = fact_sessions[duration_cols].max(axis=1).fillna(0).clip(lower=0)

    # 6. REVENUE FIELDS (0 if no purchase)
    order_cols = ['session_id', 'net_amount', 'gross_amount', 'discount_amount']
    fact_sessions = pd.merge(fact_sessions, orders[order_cols], on='session_id', how='left')
    fact_sessions[['net_amount', 'gross_amount', 'discount_amount']] = fact_sessions[['net_amount', 'gross_amount', 'discount_amount']].fillna(0)

    # 7. FINAL CLEANUP & RENAMING
    # Rename 'session_start_ts' to 'start_ts' to match requirement
    fact_sessions = fact_sessions.rename(columns={'session_start_ts': 'start_ts'})

    # Select only the required columns in the correct order
    final_cols = [
        'session_id', 'user_id', 'start_ts', 'device', 'channel', 'campaign_id', 
        'is_new_user', 'variant', 'has_product_view', 'has_add_to_cart', 
        'has_begin_checkout', 'has_payment_attempt', 'has_purchase',
        'session_duration_sec', 'time_to_cart_sec', 'time_to_checkout_sec', 
        'time_to_purchase_sec', 'time_to_payment_sec', 'net_amount', 'gross_amount', 'discount_amount'
    ]
    
    return fact_sessions[final_cols]

def create_fact_orders(data_dict):
    """
    Output 2: fact_orders.csv (1 row per order)
    Includes Basket Enrichment, Category Mix, and Margin Proxy.
    """
    orders = data_dict['orders'].copy()
    products = data_dict['products'].copy()
    items = data_dict['order_items'].copy()
    # 1. Calculate Product Costs
    basket_df = pd.merge(items, products, on='product_id', how='left')
    basket_df['item_cost'] = basket_df['quantity'] * basket_df['cost']
    basket_summary = basket_df.groupby('order_id').agg(total_items = ('quantity', 'sum'),
                                                    distinct_products = ('product_id', 'nunique'),
                                                    total_product_cost = ('item_cost', 'sum'),
                                                    average_rating = ('rating', 'mean')).reset_index()
    # 2. Categorization logic
    top_cat = basket_df.groupby(['order_id', 'category'])['item_cost'].sum().reset_index()
    top_category = top_cat.sort_values(['order_id', 'item_cost'], ascending=[True, False]).drop_duplicates('order_id').rename(columns={'category': 'top_category'})
    top_category = top_category[['order_id', 'top_category']]

    fact_orders = pd.merge(basket_summary, top_category, on='order_id', how='left')
    cat_mix = basket_df.groupby(['order_id', 'category'])['quantity'].sum().unstack(fill_value=0)
    fact_orders['category_mix'] = cat_mix.apply(lambda x: json.dumps(x[x > 0].to_dict()), axis=1).values
    # 3. Merge with main orders table to get net_amount and shipping_amount
    fact_orders = pd.merge(orders, fact_orders, on='order_id', how='left')
    # 4. MARGIN PROXY CALCULATION
    fact_orders['margin_proxy'] = fact_orders['net_amount'] - fact_orders['total_product_cost'] - fact_orders['shipping_amount']
    final_columns = ['order_id', 'session_id', 'user_id', 'order_ts', 'payment_method', 
        'net_amount', 'total_items', 'distinct_products', 'average_rating', 'margin_proxy',
        'top_category', 'category_mix']
    fact_orders = fact_orders[final_columns]

    return fact_orders

def create_dim_users(data_dict, fact_sessions, fact_orders):

    users = data_dict['users'].copy()

    user_sessions = fact_sessions.groupby('user_id').agg(lifetime_sessions = ('session_id', 'count'),
                                                        first_session_date = ('start_ts', 'min'),
                                                        last_session_date = ('start_ts', 'max')).reset_index()


    user_orders = fact_orders.groupby('user_id').agg(lifetime_orders = ('order_id', 'count'),
                                                    first_order_date = ('order_ts', 'min'),
                                                    last_order_date = ('order_ts', 'max'),
                                                    total_net_revenue = ('net_amount', 'sum'))

    dim_users = pd.merge(users, user_sessions, on='user_id', how='left')
    dim_users = pd.merge(dim_users, user_orders, on='user_id', how='left')
    # 4. DATA CLEANING (Crucial: Fill NaNs before creating flags)
    dim_users['lifetime_orders'] = dim_users['lifetime_orders'].fillna(0).astype(int)
    dim_users['lifetime_sessions'] = dim_users['lifetime_sessions'].fillna(0).astype(int)
    dim_users['total_net_revenue'] = dim_users['total_net_revenue'].fillna(0).astype(int)

    dim_users['repeat_rate_flag'] = (dim_users['lifetime_orders']>=2).astype(int)
    dim_users['user_value_band'] = 'no_spend' 
    mask = dim_users['total_net_revenue'] > 0
    if mask.any():
        dim_users.loc[mask, 'user_value_band'] = pd.qcut(
            dim_users.loc[mask, 'total_net_revenue'], 
            q=3,
            labels=['low', 'medium', 'high']
            ).astype(str)
        
    required_cols = [
            'user_id', 'signup_date', 'segment', 'city_tier', 'preferred_device',
            'lifetime_sessions', 'lifetime_orders', 'first_order_date', 
            'last_order_date', 'repeat_rate_flag', 'user_value_band'
            ]
    
    return dim_users[required_cols]

if __name__ == '__main__':
    # Cleaned data
    clean_data = extract_transform_data()
    before_capping = clean_data['orders'].copy()

    # Outlier treated data
    final_clean_data = handling_outliers(clean_data)

    # After treating the outliers
    # Identify outliers in revenue
    revenue_cols = ['net_amount', 'gross_amount', 'discount_amount']
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    # --- PLOT 1: BEFORE ---
    sns.boxplot(data=before_capping[revenue_cols], ax = axes[0])
    axes[0].set_title('BEFORE: Revenue with Outliers', fontsize=14)
    axes[0].set_ylabel('Amount (₹)')
    # --- PLOT 2: AFTER ---
    sns.boxplot(data=final_clean_data['orders'][revenue_cols], ax=axes[1])
    axes[1].set_title('AFTER: Revenue Capped (IQR Method)', fontsize=14)
    axes[1].set_ylabel('Amount (₹)')
    plt.savefig('etl/Revenue_Before_After_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()

    fact_sessions = create_fact_sessions(final_clean_data)
    save_fact_sessions = fact_sessions.to_csv('data/fact_sessions.csv', index=False)
    fact_orders = create_fact_orders(final_clean_data)
    save_fact_orders = fact_orders.to_csv('data/fact_orders.csv', index=False)
    dim_users = create_dim_users(final_clean_data, fact_sessions, fact_orders)
    save_dim_users = dim_users.to_csv('data/dim_users_enriched.csv', index=False)




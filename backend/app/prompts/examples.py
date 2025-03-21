"""
Example prompts for different use cases in the assistant UI LangGraph application.
"""

# Few-shot examples for personal finance management
PERSONAL_FINANCE_FEW_SHOT_EXAMPLE = """
Here are some examples of personal finance guidance:

User: How can I start budgeting?
Assistant: Starting a budget is a great way to take control of your finances! Here's a step-by-step approach:

1. **Track your income**: Calculate your monthly take-home pay from all sources.

2. **List your expenses**: Gather your bills, bank statements, and receipts to identify:
   - Fixed expenses (rent/mortgage, utilities, loans)
   - Variable expenses (groceries, entertainment, dining out)
   - Occasional expenses (car maintenance, gifts, medical)

3. **Categorize your spending**: Group expenses into categories like:
   - Housing (30-35% of income)
   - Transportation (10-15%)
   - Food (10-15%)
   - Utilities (5-10%)
   - Insurance (10-25%)
   - Debt repayment (15-20%)
   - Savings (10-15%)
   - Personal/Entertainment (5-10%)

4. **Choose a budgeting method**:
   - 50/30/20 rule (50% needs, 30% wants, 20% savings)
   - Zero-based budgeting (every dollar has a purpose)
   - Envelope system (cash in labeled envelopes for each category)

5. **Use tools**: Consider apps like Mint, YNAB, or even a simple spreadsheet.

6. **Review regularly**: Track your spending and adjust your budget monthly.

Would you like more specific advice on any of these steps?

User: I spent $85 at Target yesterday, how should I categorize that?
Assistant: To categorize your $85 Target purchase, I'll need a bit more information about what you bought. Target sells a wide range of products that could fall into different budget categories:

- If you bought primarily groceries and food items → Food/Groceries category
- If you bought household essentials like cleaning supplies, paper products → Household Supplies category
- If you bought clothing or personal items → Personal/Shopping category
- If you bought home decor or small furniture → Home category
- If you bought electronics or entertainment items → Entertainment/Discretionary category
- If you bought medications or health products → Healthcare/Medical category

If your purchase included items from multiple categories, you might want to split the transaction. For example, if you spent $50 on groceries and $35 on clothing, you could categorize them separately.

What types of items were included in your Target purchase?

User: How much should I be saving each month?
Assistant: The ideal amount to save each month depends on your personal financial situation, but here are some general guidelines:

**General savings recommendations:**
- Aim to save at least 15-20% of your gross income
- This includes retirement contributions, emergency fund, and other savings goals

**Priority order for savings:**
1. **Emergency fund**: Build up 3-6 months of essential expenses in an easily accessible account
2. **Retirement**: Contribute at least enough to get any employer match (free money!)
3. **High-interest debt**: Prioritize paying off debt with rates above 6-8%
4. **Additional savings goals**: Like home down payment, education, or major purchases

**Specific situations that affect savings rates:**
- Early career: Start with 10% if 20% feels impossible, then increase gradually
- Playing catch-up: If you're behind on retirement, you may need to save 25%+ of income
- High cost of living areas: You might need to adjust percentages based on housing costs
- Variable income: Save more during high-income periods to offset leaner times

Remember that some savings is better than none. If you can't hit these targets right away, start where you can and work to increase your savings rate over time.

What's your current savings rate, and do you have any specific savings goals?
"""

# Expense categorization examples
EXPENSE_CATEGORIZATION_EXAMPLE = """
Here are examples of categorizing expenses:

User: I spent $45 at the grocery store
Assistant: I'll categorize that $45 as "Groceries/Food" in your budget.

The "Groceries/Food" category typically includes:
- Food items purchased at supermarkets
- Fresh produce, meat, dairy products
- Pantry staples and ingredients for home cooking
- Non-alcoholic beverages

This category is usually considered a necessity in most budgeting systems. The typical recommended budget allocation for groceries is about 10-15% of your monthly income.

User: I paid $1,200 for rent
Assistant: I'll categorize that $1,200 as "Housing" in your budget.

The "Housing" category typically includes:
- Rent payments
- Mortgage payments
- Property taxes
- HOA fees
- Home insurance

Housing is typically the largest expense category for most households. Financial experts generally recommend keeping housing costs to 25-30% of your gross monthly income.

User: I spent $60 at a restaurant last night
Assistant: I'll categorize that $60 as "Dining Out/Restaurants" in your budget.

The "Dining Out/Restaurants" category typically includes:
- Meals at restaurants
- Food delivery services
- Take-out orders
- Coffee shops

This category is generally considered a "want" rather than a "need" in most budgeting frameworks. In the 50/30/20 budget system, it would typically fall into the 30% "wants" portion of your budget.

Most financial advisors recommend keeping dining out expenses to 5-10% of your monthly budget, though this varies based on your personal financial priorities.

User: I bought a $15 movie ticket
Assistant: I'll categorize that $15 as "Entertainment" in your budget.

The "Entertainment" category typically includes:
- Movie tickets
- Streaming services
- Concerts and live events
- Hobbies and recreational activities
- Books, music, and digital entertainment purchases

Entertainment falls into the "discretionary spending" or "wants" category in most budgeting systems. Financial experts often suggest limiting entertainment spending to about 5-10% of your monthly budget, depending on your other financial goals and obligations.

Remember that having some entertainment in your budget is important for quality of life and sustainable financial habits - the key is finding the right balance for your situation.
"""

# Chain of thought example for complex problem solving
MATH_CHAIN_OF_THOUGHT_EXAMPLE = """
Here's an example of solving a complex problem step-by-step:

User: If a store offers a "buy 2, get 1 free" promotion, and I need 14 items, how much would I save compared to buying them individually at $5 each?
Assistant: Okay, let's break this down step by step:

1.  **Calculate how many sets of 3 items you can get:** 14 items / 3 items per set = 4 sets with a remainder of 2 items.
2.  **Calculate how many free items you get:** 4 sets * 1 free item per set = 4 free items.
3.  **Calculate how many items you need to pay for:** 14 total items - 4 free items = 10 items.
4.  **Calculate the total cost:** 10 items * $5 per item = $50.
5.  **Calculate the cost of buying all items individually:** 14 items * $5 per item = $70.
6.  **Calculate the savings:** $70 - $50 = $20.

So, you would save $20 by using the "buy 2, get 1 free" promotion.
"""

# Few-shot example for financial analysis (kept for reference)
FINANCIAL_FEW_SHOT_EXAMPLE = """
Here are some examples of how to analyze stock information:

User: What do you think about AAPL stock?
Assistant: To provide an informed opinion on Apple (AAPL), I'll need to check the current stock data.

[Using get_stock_price tool for AAPL]

Based on the data, Apple (AAPL) is currently trading at $173.50, up $2.35 (1.37%) today. The company has a market cap of $2.73T and a P/E ratio of 28.5, which is relatively high but not unusual for tech companies with strong growth prospects.

Apple stock has traded between $124.17 and $198.23 over the past year. The current price is above its 52-week low but below its high, suggesting it's in a middle range.

When considering AAPL as an investment, you should look at:
1. The company's consistent innovation pipeline
2. Revenue growth and diversification beyond iPhone
3. Services segment growth and margins
4. Competition in key markets
5. Overall market conditions and tech sector performance

Would you like me to elaborate on any specific aspect of Apple's stock performance?

User: What metrics should I look at when evaluating a stock?
Assistant: When evaluating a stock, several key metrics can help you assess its value and potential:

Financial Health Metrics:
- P/E Ratio: Compares stock price to earnings per share
- PEG Ratio: P/E ratio divided by growth rate
- Debt-to-Equity: Measures financial leverage
- Current Ratio: Assesses ability to pay short-term obligations

Growth Metrics:
- Revenue Growth: Year-over-year sales increase
- Earnings Growth: Increase in profit over time
- Free Cash Flow Growth: Growth in cash generated beyond operations costs

Profitability Metrics:
- Profit Margin: Percentage of revenue that becomes profit
- Return on Equity (ROE): Efficiency at generating profits from shareholders' equity
- Return on Assets (ROA): How efficiently assets generate earnings

Valuation Metrics:
- Price-to-Sales (P/S): Stock price relative to revenue
- Price-to-Book (P/B): Stock price relative to book value
- Enterprise Value/EBITDA: Total company value relative to earnings

Dividend Metrics (if applicable):
- Dividend Yield: Annual dividend relative to share price
- Dividend Payout Ratio: Percentage of earnings paid as dividends
- Dividend Growth Rate: How fast dividends increase over time

Industry-Specific Metrics:
- Tech: Monthly active users, subscriber growth
- Retail: Same-store sales, inventory turnover
- Healthcare: Drug pipeline, patent expiration dates

Which metrics are you most interested in exploring further?
"""

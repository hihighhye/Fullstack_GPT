# InvestorGPT with Alpha Vantage

<img src="images/Flow of InvestorGPT.png" width="400" />

<br>
<br>

## Description

A Hedge Fund Manager that provides analysis of enterprise value whether its stock is worthy to buy.
It finds the stock market symbol for given company first,
and then creates analysis report of the company value considering overview, income statement and weekly stock performance of the company based on information provided by [Alpha Vantage](https://www.alphavantage.co/).
Implemented with `langchain.agents` and `langchain.tools`.

<br>

## The Structure of Agent

> - **LLM(ChatOpenAI: gpt-4o-mini) + 4 Tools + System Message** <br>

<br>

## How to declare Tool extending BaseTool

```
class CompanyOverviewToolArgsSchema(BaseModel):
    symbol:str = Field(description="Stock Symbol of the company. Example: AAPL, TSLA")

class CompanyOverviewTool(BaseTool):
    name:str = "CompanyOverview"
    description:str = """
    Use this to get an overview of the financials of the company.
    You should enter a stock symbol.
    """
    args_schema: type[CompanyOverviewToolArgsSchema] = CompanyOverviewToolArgsSchema

    def _run(self, symbol):
        ...
```

<br>
<br>
<br>

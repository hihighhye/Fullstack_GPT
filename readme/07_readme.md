# InvestorGPT with Yahoo Finance

<img src="images/Flow of InvestorGPT_2.png" height="400" />

<br>
<br>

## Description

A Hedge Fund Manager that provides analysis of enterprise value whether its stock is worthy to buy.
It finds the stock market symbol for given company first,
and then creates analysis report of the company value considering income statement, balance sheets and 3-month daily stock performance of the company based on information provided by [YFinance](#how-to-use-yfinance).<br>
Implemented with [OpenAI Assistant](https://platform.openai.com/playground/assistants).

<br>

## How to use YFinance

```
pip install yfinance openai --upgrade
```

<br>

## The Structure of Assistant

> - **LLM(ChatOpenAI: gpt-4o-mini) + 4 Functions + instructions** <br>

<br>

## How to declare Functions for the Assistant parameter

```
functions = [
    {
        "type": "function",
        "function": {
            "name": "get_ticker",
            "description": "Given the name of a company returns its ticker symbol. \
                Do NOT append any other comment except the ticker symbol. (e.g. AAPL)",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {
                        "type": "string",
                        "description": "The name of the company"
                    }
                },
                "required": ["company_name"],
            }
        }
    },
    ...
]
```

<br>
<br>
<br>

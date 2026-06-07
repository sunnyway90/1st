import json
import unittest

from scripts.download_us_daily import (
    is_stock_like_security,
    parse_nasdaq_listed,
    parse_other_listed,
    parse_yahoo_chart,
    safe_filename,
    to_yahoo_symbol,
)


class DownloadUsDailyTests(unittest.TestCase):
    def test_parse_nasdaq_listed_filters_test_issues_and_etfs_by_default(self):
        text = "\n".join(
            [
                "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares",
                "AAPL|Apple Inc. - Common Stock|Q|N|N|100|N|N",
                "QQQ|Invesco QQQ Trust|G|N|N|100|Y|N",
                "AACBU|Artius II Acquisition Inc. - Unit|G|N|N|100|N|N",
                "TEST|Test Company|Q|Y|N|100|N|N",
                "File Creation Time: 0607202600:00|||||||",
            ]
        )

        symbols = parse_nasdaq_listed(text, include_etfs=False)

        self.assertEqual([symbol.ticker for symbol in symbols], ["AAPL"])

    def test_parse_other_listed_can_include_etfs(self):
        text = "\n".join(
            [
                "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol",
                "BRK.B|Berkshire Hathaway Inc.|N|BRK.B|N|100|N|BRK.B",
                "SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY",
                "FAKE|Fake Test|A|FAKE|N|100|Y|FAKE",
                "File Creation Time: 0607202600:00|||||||",
            ]
        )

        symbols = parse_other_listed(text, include_etfs=True)

        self.assertEqual([symbol.ticker for symbol in symbols], ["BRK.B", "SPY"])
        self.assertEqual(symbols[0].exchange, "NYSE")
        self.assertTrue(symbols[1].is_etf)

    def test_is_stock_like_security_excludes_non_stock_instruments(self):
        self.assertTrue(is_stock_like_security("Apple Inc. - Common Stock"))
        self.assertTrue(is_stock_like_security("Infosys Limited American Depositary Shares"))
        self.assertFalse(is_stock_like_security("Example Corp. - Unit"))
        self.assertFalse(is_stock_like_security("Example Corp. - Warrants"))
        self.assertFalse(is_stock_like_security("Example Corp. 6.50% Senior Notes due 2030"))

    def test_yahoo_symbol_and_safe_filename(self):
        self.assertEqual(to_yahoo_symbol("BRK.B"), "BRK-B")
        self.assertEqual(to_yahoo_symbol("BF/B"), "BF-B")
        self.assertEqual(safe_filename("BAD:SYMBOL"), "BAD_SYMBOL")

    def test_parse_yahoo_chart_skips_rows_without_prices(self):
        payload = {
            "chart": {
                "result": [
                    {
                        "timestamp": [1262563200, 1262649600],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [10.0, None],
                                    "high": [11.0, None],
                                    "low": [9.5, None],
                                    "close": [10.5, None],
                                    "volume": [1000, None],
                                }
                            ],
                            "adjclose": [{"adjclose": [10.1, None]}],
                        },
                    }
                ],
                "error": None,
            }
        }

        rows = parse_yahoo_chart(json.dumps(payload))

        self.assertEqual(
            rows,
            [
                {
                    "Date": "2010-01-04",
                    "Open": 10.0,
                    "High": 11.0,
                    "Low": 9.5,
                    "Close": 10.5,
                    "Adj Close": 10.1,
                    "Volume": 1000,
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()

"""Offline tests for the parser. Run: python -m unittest -v test_scraper.py

The HTML below is trimmed from a real MD Computers search page (Oct 2026),
plus one hand-written card without a discount to cover that branch.
"""

import unittest

from mdcomputers_scraper import parse_page, parse_price

PAGE_HTML = """
<div class="header"><div class="product-grid-item">
  <h3 class="product-entities-title"><a href="/menu-widget">Menu widget, not a result</a></h3>
</div></div>
<div id="content">
  <div class="product-grid-item"><div class="product-wrapper">
    <button onclick="if (!window.__cfRLUnblockHandlers) return false; cart.add('16447');">Add to Cart</button>
    <h3 class="product-entities-title"><a href="https://mdcomputers.in/product/seagate-expansion-1tb-external-hard-drive-stkm1000400">Seagate Expansion 1TB External Hard Drive</a></h3>
    <span class="price"><span class="del"><span class=" amount">₹10,000</span></span><span class="ins"><span class=" amount"> ₹9,160</span></span></span>
  </div></div>
  <div class="product-grid-item"><div class="product-wrapper">
    <h3 class="product-entities-title"><a href="https://mdcomputers.in/product/plain">Plain Price Drive</a></h3>
    <span class="price"><span class=" amount">₹4,500</span></span>
  </div></div>
  <div class="col-md-6 text-md-end mb-2">Showing 1 to 20 of 46 (3 Pages)</div>
</div>
"""


class ParserTests(unittest.TestCase):
    def test_parse_price(self):
        self.assertEqual(parse_price("₹1,299"), 1299)
        self.assertEqual(parse_price(" ₹ 16,660 "), 16660)
        self.assertIsNone(parse_price(""))
        self.assertIsNone(parse_price(None))

    def test_parse_page(self):
        products, total_pages = parse_page(PAGE_HTML)
        self.assertEqual(total_pages, 3)
        self.assertEqual(len(products), 2)  # header widget is ignored

        discounted, plain = products
        self.assertEqual(discounted.product_id, "16447")
        self.assertEqual(discounted.name, "Seagate Expansion 1TB External Hard Drive")
        self.assertEqual((discounted.price, discounted.mrp, discounted.discount_percent), (9160, 10000, 8))

        self.assertIsNone(plain.product_id)
        self.assertEqual((plain.price, plain.mrp, plain.discount_percent), (4500, None, None))

    def test_empty_page(self):
        self.assertEqual(parse_page("<div id='content'>No product matches</div>"), ([], 0))


if __name__ == "__main__":
    unittest.main()

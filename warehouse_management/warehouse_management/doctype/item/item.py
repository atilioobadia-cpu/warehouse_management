# Copyright (c) 2026, X Electronics and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Item(Document):
	def autoname(self):
		if not self.item_code:
			self.item_code = frappe.model.naming.make_autoname("ITEM-.#####")
		self.name = self.item_code

	def before_save(self):
		if not self.item_code:
			self.item_code = frappe.model.naming.make_autoname("ITEM-.#####")
		self.name = self.item_code

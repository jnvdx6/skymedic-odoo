# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install")
class TestShippingShipment(TransactionCase):
    """Test shipping.shipment model functionality."""

    def setUp(self):
        super().setUp()
        self.company = self.env.ref("base.main_company")

        self.customer = self.env["res.partner"].create({
            "name": "Test Customer",
            "street": "Test Street 123",
            "city": "Madrid",
            "zip": "28001",
            "country_id": self.env.ref("base.es").id,
            "phone": "912345678",
            "is_company": True,
        })

        self.product = self.env["product.product"].create({
            "name": "Test Product",
            "type": "consu",
            "weight": 1.5,
            "list_price": 100.0,
        })

        delivery_product = self.env["product.product"].create({
            "name": "Delivery",
            "type": "service",
        })

        self.carrier = self.env["delivery.carrier"].create({
            "name": "Test Carrier",
            "delivery_type": "fixed",
            "product_id": delivery_product.id,
            "fixed_price": 10.0,
        })

    def _create_picking(self):
        picking = self.env["stock.picking"].create({
            "partner_id": self.customer.id,
            "picking_type_id": self.env.ref("stock.picking_type_out").id,
            "location_id": self.env.ref("stock.stock_location_stock").id,
            "location_dest_id": self.env.ref(
                "stock.stock_location_customers"
            ).id,
            "carrier_id": self.carrier.id,
            "origin": "SO001",
        })
        self.env["stock.move"].create({
            "product_id": self.product.id,
            "product_uom_qty": 1,
            "product_uom": self.product.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "picking_id": picking.id,
        })
        return picking

    def _create_shipment(self, picking=None, **kwargs):
        if picking is None:
            picking = self._create_picking()
        vals = {
            "picking_id": picking.id,
            "carrier_id": self.carrier.id,
            "tracking_ref": "TRACK123",
            **kwargs,
        }
        return self.env["shipping.shipment"].create(vals)

    # ---- Tests ----

    def test_shipment_creation_with_sequence(self):
        """Test: shipment gets auto-generated sequence name."""
        shipment = self._create_shipment()
        self.assertTrue(shipment.name.startswith("SHIP/"))
        self.assertEqual(shipment.state, "draft")
        self.assertEqual(shipment.carrier_id, self.carrier)
        self.assertEqual(shipment.tracking_ref, "TRACK123")

    def test_shipment_partner_from_picking(self):
        """Test: partner is auto-filled from picking."""
        picking = self._create_picking()
        shipment = self._create_shipment(picking=picking)
        self.assertEqual(shipment.partner_id, self.customer)
        self.assertEqual(shipment.origin, "SO001")

    def test_state_transition_draft_to_confirmed(self):
        """Test: draft → confirmed transition."""
        shipment = self._create_shipment()
        self.assertEqual(shipment.state, "draft")
        shipment.action_confirm()
        self.assertEqual(shipment.state, "confirmed")
        self.assertTrue(shipment.ship_date)

    def test_state_transition_confirmed_to_in_transit(self):
        """Test: confirmed → in_transit transition."""
        shipment = self._create_shipment()
        shipment.action_confirm()
        shipment.action_mark_in_transit()
        self.assertEqual(shipment.state, "in_transit")

    def test_state_transition_in_transit_to_delivered(self):
        """Test: in_transit → delivered transition."""
        shipment = self._create_shipment()
        shipment.action_confirm()
        shipment.action_mark_in_transit()
        shipment.action_mark_delivered()
        self.assertEqual(shipment.state, "delivered")
        self.assertTrue(shipment.delivery_date)

    def test_state_transition_to_returned(self):
        """Test: in_transit → returned transition."""
        shipment = self._create_shipment()
        shipment.action_confirm()
        shipment.action_mark_in_transit()
        shipment.action_mark_returned()
        self.assertEqual(shipment.state, "returned")

    def test_cancellation(self):
        """Test: cancel a draft shipment."""
        shipment = self._create_shipment()
        shipment.action_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_reset_to_draft(self):
        """Test: cancelled → draft transition."""
        shipment = self._create_shipment()
        shipment.action_cancel()
        shipment.action_reset_to_draft()
        self.assertEqual(shipment.state, "draft")

    def test_invalid_state_transition_ignored(self):
        """Test: invalid transitions are silently ignored."""
        shipment = self._create_shipment()
        # draft → in_transit should be ignored (must be confirmed first)
        shipment.action_mark_in_transit()
        self.assertEqual(shipment.state, "draft")

    def test_auto_creation_on_picking(self):
        """Test: shipment auto-created via _create_shipping_shipment."""
        picking = self._create_picking()
        picking.carrier_tracking_ref = "AUTO123"
        picking.carrier_price = 15.0
        shipment = picking._create_shipping_shipment()
        self.assertTrue(shipment)
        self.assertEqual(shipment.tracking_ref, "AUTO123")
        self.assertEqual(shipment.shipping_cost, 15.0)
        self.assertEqual(shipment.state, "confirmed")

    def test_auto_creation_no_duplicate(self):
        """Test: duplicate shipment is not created."""
        picking = self._create_picking()
        picking.carrier_tracking_ref = "NODUP123"
        picking.carrier_price = 10.0
        shipment1 = picking._create_shipping_shipment()
        shipment2 = picking._create_shipping_shipment()
        self.assertEqual(shipment1, shipment2)

    def test_auto_creation_skipped_without_tracking(self):
        """Test: no shipment created if no tracking ref."""
        picking = self._create_picking()
        result = picking._create_shipping_shipment()
        self.assertFalse(result)

    def test_shipment_count_on_picking(self):
        """Test: shipment count computed on picking."""
        picking = self._create_picking()
        self.assertEqual(picking.shipment_count, 0)
        self._create_shipment(picking=picking)
        picking.invalidate_recordset(["shipment_count"])
        self.assertEqual(picking.shipment_count, 1)

    def test_label_count(self):
        """Test: label count with no labels is zero."""
        shipment = self._create_shipment()
        self.assertEqual(shipment.label_count, 0)

    def test_label_creation_and_count(self):
        """Test: shipping.label linked to shipment is counted."""
        shipment = self._create_shipment()
        attachment = self.env["ir.attachment"].create({
            "name": "test_label.pdf",
            "type": "binary",
            "datas": "dGVzdA==",  # base64("test")
            "res_model": "shipping.shipment",
            "res_id": shipment.id,
            "mimetype": "application/pdf",
        })
        self.env["shipping.label"].create({
            "shipment_id": shipment.id,
            "attachment_id": attachment.id,
            "label_type": "shipping",
        })
        shipment.invalidate_recordset(["label_ids", "label_count"])
        self.assertEqual(shipment.label_count, 1)

    def test_label_download(self):
        """Test: label download action returns URL."""
        shipment = self._create_shipment()
        attachment = self.env["ir.attachment"].create({
            "name": "test_label.pdf",
            "type": "binary",
            "datas": "dGVzdA==",
            "res_model": "shipping.shipment",
            "res_id": shipment.id,
            "mimetype": "application/pdf",
        })
        label = self.env["shipping.label"].create({
            "shipment_id": shipment.id,
            "attachment_id": attachment.id,
        })
        result = label.action_download()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertIn(str(attachment.id), result["url"])

    def test_label_name_computed(self):
        """Test: label name is computed from shipment and tracking."""
        shipment = self._create_shipment()
        attachment = self.env["ir.attachment"].create({
            "name": "test.pdf",
            "type": "binary",
            "datas": "dGVzdA==",
            "res_model": "shipping.shipment",
            "res_id": shipment.id,
            "mimetype": "application/pdf",
        })
        label = self.env["shipping.label"].create({
            "shipment_id": shipment.id,
            "attachment_id": attachment.id,
        })
        self.assertIn(shipment.name, label.name)
        self.assertIn("TRACK123", label.name)

    def test_download_label_no_labels(self):
        """Test: downloading label with no labels raises error."""
        shipment = self._create_shipment()
        with self.assertRaises(UserError):
            shipment.action_download_label()

    def test_cron_runs_without_error(self):
        """Test: cron method runs without error on empty set."""
        self.env["shipping.shipment"]._cron_update_tracking_status()

    def test_cron_processes_active_shipments(self):
        """Test: cron processes confirmed shipments."""
        shipment = self._create_shipment()
        shipment.action_confirm()
        # Cron should run without error (no actual API call for fixed carrier)
        self.env["shipping.shipment"]._cron_update_tracking_status()

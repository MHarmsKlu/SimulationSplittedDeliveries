from datetime import datetime

class Order_SKU: 
    def __init__(self, sku_id,  order_placed, quantity,verbose=False ):
        self.id = sku_id
        self.placed = order_placed
        self.quantity = quantity
        self.delivered_quantity = 0
        self.shipments = []
        self.complete = False
        self.verbose = verbose

    def update(self, shipment):
        self.shipments.append(shipment)
        self.delivered_quantity += shipment.SKUs[self.id]

        if self.quantity == self.delivered_quantity:
            self.complete = True
            self.completed = shipment.delivery_date

class Order:
    def __init__(self, id, order_placed, sku_configs):
        self.id = id
        self.placed = order_placed
        self.complete = False
        self.SKUs = {}
        for sku,qty in sku_configs.items():
            self.SKUs[sku] = Order_SKU(sku, self.placed, qty )

    def update(self, shipment):
        complete = True
        for sku in shipment.SKUs.keys():
            self.SKUs[sku].update(shipment)
            if not self.SKUs[sku].complete:
                complete = False
        if complete:
            self.complete = True
        
        
class Shipment:
    def __init__(self,ship_id, order_id, goods, delivery_date):
        self.ship_id = ship_id
        self.order_id = order_id
        self.SKUs = goods
        self.delivery_date = delivery_date

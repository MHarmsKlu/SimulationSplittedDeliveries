from datetime import datetime

class Order: 
    def __init__(self, id,  order_placed, quantity,verbose=False ):
        self.id = id
        self.placed = order_placed
        self.quantity = quantity
        self.delivered_quantity = 0
        self.shipments = []
        self.complete = False
        self.verbose = verbose

    def update(self, shipment):
        self.shipments.append(shipment)
        self.delivered_quantity += shipment.quantity

        if self.quantity == self.delivered_quantity:
            self.complete = True
            if self.verbose:
                print(f"order {self.id} complete")
            self.completed = shipment.delivery_date

class Shipment:
    def __init__(self,ship_id, order_id,quantity, delivery_date):
        self.ship_id = ship_id
        self.order_id = order_id
        self.quantity = quantity
        self.delivery_date = delivery_date

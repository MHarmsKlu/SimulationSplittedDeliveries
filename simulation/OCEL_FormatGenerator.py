import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

def convert_int64_to_int(obj):
    """
    Recursively converts numpy.int64 values to regular Python int.
    """
    if isinstance(obj, dict):
        return {key: convert_int64_to_int(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_int64_to_int(item) for item in obj]
    elif isinstance(obj, np.int64):  # Convert numpy int64 to native int
        return int(obj)
    return obj


# Function to save the OCEL log in JSON format
def save_ocel_log_to_json(ocel_log, start_date, verbose=False):
    # Convert any np.int64 values to regular Python int
    ocel_log = convert_int64_to_int(ocel_log)

    # Create the Output directory if it does not exist
    output_dir = "Output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Create the filename with the format "OrderProcess_<StartDate>.json"
    date_str = start_date.strftime("%Y-%m-%d")
    filename = f"OrderProcess_{date_str}.json"
    file_path = os.path.join(output_dir, filename)

    # Save the OCEL log in JSON format
    with open(file_path, "w") as f:
        json.dump(ocel_log, f, indent=4)

    # Print the path where the OCEL log has been saved
    if verbose:
        print(f"OCEL Log saved at: {file_path}")


used_ids = {}
used_ids["order"] = set()
used_ids["item"] = set()
used_ids["package"] = set()

def generate_unique_id(obj_type,iteration):
    while True:
        rand_num = np.random.randint(1000, 9999)
        obj_id = f"{obj_type}_{iteration}_{rand_num}"
        if obj_id not in used_ids[obj_type]:
            used_ids[obj_type].add(obj_id)
            return obj_id

# Helper function to generate random timedelta in a realistic working day range
def generate_random_timedelta(min_days, max_days, min_hours=8, max_hours=17, verbose=False):
    """
    Generate a random timedelta with a random number of days between `min_days` and `max_days`
    and random hours between `min_hours` and `max_hours` (within working hours).
    """
    days = np.random.randint(min_days, max_days)
    hours = np.random.randint(min_hours, max_hours)
    minutes = np.random.randint(0, 59)
    return timedelta(days=days, hours=hours, minutes=minutes)


# Function to adjust the date to avoid weekends
def adjust_to_weekday(date):
    # If the date is a Saturday (5) or Sunday (6), shift to Monday
    while date.weekday() >= 5:
        date += timedelta(days=1)
    return date


# Helper function to adjust time to working hours (08:00 - 17:00) and weekdays
def adjust_to_working_hours(timestamp):
    # Adjust to the nearest working day if it's a weekend
    timestamp = adjust_to_weekday(timestamp)

    # Adjust the time if it's outside of working hours (08:00 to 17:00)
    if timestamp.hour < 8:
        timestamp = timestamp.replace(hour=8, minute=np.random.randint(0, 59))
    elif timestamp.hour >= 17:
        # Move the timestamp to the next working day at a random time between 08:00 and 17:00
        timestamp += timedelta(days=1)
        timestamp = timestamp.replace(hour=8, minute=np.random.randint(0, 59))

    return timestamp

def distribute_values(func, time_slots, target_sum, verbose=False):
    """
    Distributes values based on a given function and adapts to target values while maintaining the original function's shape.
    Ensures that no value falls below a threshold (Amount * normalized value >= 1).
    Prioritizes reducing values that are closer to their target based on the function.

    :param func: The mathematical function (e.g., lambda x: x**2)
    :param time_slots: Number of time slots (del_days)
    :param target_sum: Target value to be reached
    :return: List of calculated values
    """
    x_values = np.arange(1, time_slots + 1)
    y_values = np.array([func(x) for x in x_values])

    if verbose:
        print("Initial function values:", y_values)

    # Shift values to make them positive
    if np.isscalar(y_values):
        y_values = np.full_like(x_values, y_values)

    min_val, max_val = np.min(y_values), np.max(y_values)
    y_values = y_values - min_val + 1  # Shift to positive values
    if verbose:
        print("Shifted function values (positive):", y_values)

    # Normalize function values so that their sum is 1
    normalized_y_values = y_values / np.sum(y_values)
    if verbose:
        print("Normalized function values (sum=1):", normalized_y_values)
    if verbose:
        print("Sum of normalized values:", np.sum(normalized_y_values))

    # Adjust the values using weighted rounding based on residuals
    raw_values = target_sum * normalized_y_values
    floored_values = np.floor(raw_values).astype(int)
    residuals = raw_values - floored_values

    # Ensure minimum value of 1
    floored_values = np.maximum(floored_values, 1)

    # Recalculate surplus after enforcing the minimum
    surplus = target_sum - np.sum(floored_values)
    if verbose:
        print("Adjusted values (after floor and min check):", floored_values)
        print("Surplus to distribute:", surplus)

    # Distribute surplus based on highest residuals
    if surplus > 0:
        indices = np.argsort(-residuals)  # descending order
        for i in indices:
            floored_values[i] += 1
            surplus -= 1
            if surplus == 0:
                break
    elif surplus < 0:
        # Use normalized_y_values to determine proportional reduction weights
        weights = normalized_y_values / np.sum(normalized_y_values)
        # Invert weights so that higher values get reduced more
        reduction_weights = weights / np.sum(weights)

        # Compute desired number of reductions per index
        total_reductions = -surplus
        raw_reductions = total_reductions * reduction_weights
        floored_reductions = np.floor(raw_reductions).astype(int)
        residuals = raw_reductions - floored_reductions

        # Distribute remaining reductions based on fractional parts
        remainder = total_reductions - np.sum(floored_reductions)
        extra_indices = np.argsort(-residuals)
        for i in extra_indices[:remainder]:
            floored_reductions[i] += 1

        # Apply the reductions while ensuring no value goes below 1
        for i in range(len(floored_values)):
            max_reducible = floored_values[i] - 1
            reduction = min(floored_reductions[i], max_reducible)
            floored_values[i] -= reduction
            surplus += reduction  # surplus is negative, so this moves toward zero

    adjusted_values = floored_values
    if verbose:
        print("Final adjusted values:", adjusted_values)
        print("Sum of final result:", np.sum(adjusted_values))

    return adjusted_values.tolist()


# Function to generate OCEL event log
def generate_ocel_event_log(start_date, amount, func, del_days, iteration, company="company_1", verbose=False):

    object_types = [
        {
            "name": "Order",
            "attributes": [
                {"name": "id", "type": "string"},
                {"name": "amount", "type": "int"}
            ]
        },
        {
            "name": "Item",
            "attributes": [
                {"name": "id", "type": "string"},
                {"name": "amount", "type": "int"}
            ]
        },
        {
            "name": "Package",
            "attributes": [
                {"name": "id", "type": "string"},
                {"name": "amount", "type": "int"}
            ]
        }
    ]

    event_types = [
        {
            "name": "Place Order",
            "attributes": [
                {"name": "company", "type": "string"}
            ]
        },
        {
            "name": "Send Invoice",
            "attributes": [
                {"name": "company", "type": "string"}
            ]
        },
        {
            "name": "Receive Payment",
            "attributes": [
                {"name": "company", "type": "string"},
                {"name": "payment_method", "type": "string"}
            ]
        },
        {
            "name": "Check Availability",
            "attributes": [
                {"name": "checker", "type": "string"}
            ]
        },
        {
            "name": "Split Item",
            "attributes": [
                {"name": "spliter", "type": "string"},
            ]
        },
        {
            "name": "Pick Item",
            "attributes": [
                {"name": "picker", "type": "string"}
            ]
        },
        {
            "name": "Pack Items",
            "attributes": [
                {"name": "packer", "type": "string"}
            ]
        },
        {
            "name": "Store Package",
            "attributes": [
                {"name": "storer", "type": "string"}
            ]
        },
        {
            "name": "Load Package",
            "attributes": [
                {"name": "loader", "type": "string"}
            ]
        },
        {
            "name": "Deliver Package",
            "attributes": [
                {"name": "logistics_company", "type": "string"}
            ]
        }
    ]

    objects = []

    # List of Warehouse Employees
    warehouse_employees = [
        "J. Williams",
        "E. Davis",
        "D. Brown",
        "S. Wilson",
        "L. Moore",
        "O. Garcia"
    ]

    # List of Shipping Companies
    shipping_companies = [
        "DHL",
        "UPS",
        "FedEx"
    ]

    payment_methods = [
        "Credit Card",
        "PayPal",
        "Bank Transfer"
    ]

    # Generate order_id for consistency across all activities
    order_id = f"order_{iteration}"
    item_id = generate_unique_id("item",iteration)

    # Adjust start date to ensure it's a weekday
    start_date = adjust_to_weekday(start_date)

    # Generate timestamps for each event based on the start date
    place_order_timestamp = start_date
    send_invoice_timestamp = place_order_timestamp + generate_random_timedelta(1, 3)  # 1-3 days for invoice
    receive_payment_timestamp = send_invoice_timestamp + generate_random_timedelta(1, 7)  # 1-7 days for payment

    # Distribute values for the amount to determine when to check availability
    check_availability_days = distribute_values(func, del_days, amount)

    order_object = {
        "id": order_id,
        "type": "Order",
        "attributes": [
            {
                "name": "amount",
                "time": place_order_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "value": amount
            }
        ],
        "relationships":
            [
                {
                    "objectId": item_id,
                    "qualifier": "Item of Order"
                }
            ]
    }

    # Append the Order object to the list of objects
    objects.append(order_object)

    # Create events for the log
    events = [
        {
            "id": f"e_{iteration}_1_{company}",
            "type": "Place Order",
            "time": place_order_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "company",
                    "value": company
                }

            ],
            "relationships": [
                {
                    "objectId": order_id,
                    "qualifier": "Regular placement of order"
                },
                {
                    "objectId": item_id,
                    "qualifier": "Regular placement of order"
                }
            ],
        },
        {
            "id": f"e_{iteration}_2_{company}",
            "type": "Send Invoice",
            "time": send_invoice_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "company",
                    "value": company
                }
            ],
            "relationships": [
                {
                    "objectId": order_id,
                    "qualifier": "Regular placement of order"
                }
            ],

        },
        {
            "id": f"e_{iteration}_3_{company}",
            "type": "Receive Payment",
            "time": receive_payment_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "company",
                    "value": company
                },
                {
                    "name": "payment_method",
                    "value": np.random.choice(payment_methods)
                }
            ],
            "relationships": [
                {
                    "objectId": order_id,
                    "qualifier": "Regular placement of order"
                }
            ],
        }
    ]

    # Now add the "Check Availability" events based on the distributed days
    last_check_timestamp = place_order_timestamp
    last_item_id = item_id  # Start with the initial item_id

    # Initialize the del_amount variable to track the cumulative available amount
    del_amount = 0  # Start with a cumulative amount of 0

    split_item_timestamp = place_order_timestamp

    # Loop through all the `Check Availability` events
    for i, check_day in enumerate(check_availability_days):
        # Calculate the timestamp for the next "Check Availability"
        check_availability_timestamp = last_check_timestamp
        check_availability_timestamp += generate_random_timedelta(1, 7)  # Add a random time offset
        check_availability_timestamp = adjust_to_working_hours(check_availability_timestamp)

        # Add the current available amount to del_amount
        del_amount += check_availability_days[i]

        # Add the "Check Availability" event
        events.append({
            "id": f"e_{iteration}_{i}_4_{company}",
            "type": "Check Availability",
            "time": check_availability_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "checker",
                    "value": np.random.choice(warehouse_employees)
                }
            ],
            "relationships": [
                {
                    "objectId": last_item_id,
                    "qualifier": "Regular availability check of items"
                }
            ]
        })

        # Debugging print statement to track the process
        if verbose:
            print(f"Checking availability for item {last_item_id} at {check_availability_timestamp}")
            print(f"Cumulative available amount (del_amount): {del_amount}")

        # Check if del_amount is still less than the total amount
        if del_amount < amount:
            # Trigger Split Item if the condition is met
            new_item_id_1 = generate_unique_id("item",iteration)
            new_item_id_2 = generate_unique_id("item",iteration)

            # Print debug for Split Item
            if verbose:
                print(f"Split Item triggered! New item IDs: {new_item_id_1}, {new_item_id_2}")


            item_object = {
                "id": last_item_id,
                "type": "Item",
                "attributes": [
                    {
                        "name": "amount",
                        "time": split_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                        "value": amount - del_amount + check_availability_days[i]
                    }
                ],
                "relationships":
                    [
                        {
                            "objectId": new_item_id_1,
                            "qualifier": "Split item out stock"
                        },
                        {
                            "objectId": new_item_id_2,
                            "qualifier": "Split item deliver"
                        }
                    ]
            }

            # Append the Order object to the list of objects
            objects.append(item_object)

            # Add the "Split Item" event (1 day after Check Availability)
            split_item_timestamp = check_availability_timestamp + timedelta(days=1)

            events.append({
                "id": f"e_{iteration}_{i}_5_{company}",
                "type": "Split Item",
                "time": split_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "attributes": [
                    {
                        "name": "spliter",
                        "value": np.random.choice(warehouse_employees)
                    }
                ],
                "relationships": [
                    {
                        "objectId": last_item_id,
                        "qualifier": "Split of available items for delivery"
                    },
                    {
                        "objectId": new_item_id_1,
                        "qualifier": "Split item out of stock"
                    },
                    {
                        "objectId": new_item_id_2,
                        "qualifier": "Split item for delivery"
                    }
                ]
            })

            item_object_del = {
                "id": new_item_id_2,
                "type": "Item",
                "attributes": [
                    {
                        "name": "amount",
                        "time": split_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                        "value": check_availability_days[i]
                    }
                ],
                "relationships":
                    [
                        {
                            "objectId": last_item_id,
                            "qualifier": "Split out of item"
                        },
                        {
                            "objectId": new_item_id_1,
                            "qualifier": "Split item out of stock"
                        }
                    ]
            }

            # Append the Order object to the list of objects
            objects.append(item_object_del)

            # Set the last_item_id to the first new item_id for future events
            last_item_id = new_item_id_1

        else:
            item_object = {
                "id": last_item_id,
                "type": "Item",
                "attributes": [
                    {
                        "name": "amount",
                        "time": split_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                        "value": amount - del_amount + check_availability_days[i]
                    }
                ],
                "relationships":
                    [
                    ]
            }

            # Append the Order object to the list of objects
            objects.append(item_object)

        # Update the last timestamp for future events
        last_check_timestamp = check_availability_timestamp

        # After Split Item or Check Availability, execute the "Pick Item" activity
        if del_amount < amount:
            # If a Split Item occurred, use the new item_id_2 for Pick Item
            pick_item_timestamp = split_item_timestamp + timedelta(
                minutes=np.random.randint(15, 180))  # 15 mins to 3 hours
            pick_item_timestamp = adjust_to_working_hours(pick_item_timestamp)
            events.append({
                "id": f"e_{iteration}_{i}_6_{company}",
                "type": "Pick Item",
                "time": pick_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),

                "attributes": [
                    {
                        "name": "picker",
                        "value": np.random.choice(warehouse_employees)
                    }
                ],
                "relationships": [
                    {
                        "objectId": new_item_id_2,
                        "qualifier": "Regular pick of item"
                    }
                ]
            })
            if verbose:
                print(f"Pick Item activity for {new_item_id_2} after Split Item at {pick_item_timestamp}")
        else:
            # If no Split Item occurred, use the item_id from Check Availability for Pick Item
            pick_item_timestamp = check_availability_timestamp + timedelta(
                minutes=np.random.randint(15, 180))  # 15 mins to 3 hours
            pick_item_timestamp = adjust_to_working_hours(pick_item_timestamp)
            events.append({
                "id": f"e_{iteration}_{i}_7_{company}",
                "type": "Pick Item",
                "time": pick_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "attributes": [
                    {
                        "name": "picker",
                        "value": np.random.choice(warehouse_employees)
                    }
                ],
                "relationships": [
                    {
                        "objectId": last_item_id,
                        "qualifier": "Regular pick of item"
                    }
                ]
            })
            if verbose:
                print(f"Pick Item activity for {last_item_id} after Check Availability at {pick_item_timestamp}")

        # After Pick Item, execute the "Pack Items" activity
        pack_items_timestamp = pick_item_timestamp + timedelta(minutes=np.random.randint(5, 60))  # 5 minutes to 1 hour
        pack_items_timestamp = adjust_to_working_hours(pack_items_timestamp)

        package_id = generate_unique_id("package", iteration)
        package_object = {
            "id": package_id,
            "type": "Package",
            "attributes": [
                {
                    "name": "amount",
                    "time": pack_items_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                    "value": check_availability_days[i]
                }
            ],
            "relationships":
                [
                    {
                        "objectId": last_item_id,
                        "qualifier": "Package of item"
                    }
                ]
        }

        # Append the Package object to the list of objects
        objects.append(package_object)

        # Add the "Pack Items" activity
        events.append({
            "id": f"e_{iteration}_{i}_8_{company}",
            "type": "Pack Items",
            "time": pack_items_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "packer",
                    "value": np.random.choice(warehouse_employees)
                }
            ],
            "relationships": [
                {
                    "objectId": last_item_id,
                    "qualifier": "Regular pack of item"
                }
            ]
        })
        if verbose:
            print(f"Pack Items activity for {last_item_id} with package {package_id} at {pack_items_timestamp}")

        # After Pack Items, execute the "Store Package" activity
        store_package_timestamp = pack_items_timestamp + timedelta(minutes=np.random.randint(5, 20))  # 5 to 20 minutes
        store_package_timestamp = adjust_to_working_hours(store_package_timestamp)
        # Add the "Store Package" activity
        events.append({
            "id": f"e_{iteration}_{i}_9_{company}",
            "type": "Store Package",
            "time": store_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "storer",
                    "value": np.random.choice(warehouse_employees)
                }
            ],
            "relationships": [
                {
                    "objectId": package_id,
                    "qualifier": "Regular store of package"
                }
            ]
        })
        if verbose:
            print(f"Store Package activity for {package_id} at {store_package_timestamp}")

        # After Store Package, execute the "Load Package" activity
        load_package_timestamp = store_package_timestamp + timedelta(
            minutes=np.random.randint(20, 360))  # 20 minutes to 6 hours
        load_package_timestamp = adjust_to_working_hours(load_package_timestamp)
        # Add the "Load Package" activity
        events.append({
            "id": f"e_{iteration}_{i}_10_{company}",
            "type": "Load Package",
            "time": load_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "loader",
                    "value": np.random.choice(warehouse_employees)
                }
            ],
            "relationships": [
                {
                    "objectId": package_id,
                    "qualifier": "Regular load of package"
                }
            ]
        })
        if verbose:
            print(f"Load Package activity for {package_id} at {load_package_timestamp}")

        # After Load Package, execute the "Deliver Package" activity
        deliver_package_timestamp = load_package_timestamp + timedelta(days=np.random.randint(3, 6))  # 3 to 6 days
        # Add the "Deliver Package" activity
        events.append({
            "id": f"e_{iteration}_{i}_11_{company}",
            "type": "Deliver Package",
            "time": deliver_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "attributes": [
                {
                    "name": "logistics_company",
                    "value": np.random.choice(shipping_companies)
                }
            ],
            "relationships": [
                {
                    "objectId": package_id,
                    "qualifier": "Regular deliver of package"
                }
            ]
        })
        if verbose:
            print(f"Deliver Package activity for {package_id} at {deliver_package_timestamp}")

    ocel_log = {
        "objectTypes": object_types,
        "eventTypes": event_types,
        "objects": objects,
        "events": events
    }

    # Save the OCEL log as a JSON file
    save_ocel_log_to_json(ocel_log, start_date,verbose)

    return ocel_log


# Example usage of the function
start_date = datetime(2025, 4, 7, 8, 0, 0)  # Example start date (Monday, 8 AM)
amount = 800  # Example amount for the order
func = lambda x: np.exp(2 * x)  # Example function for distributing the amount over time
del_days = 20  # Test with 10 days

# # Generate the OCEL event log
# ocel_event_log = generate_ocel_event_log(start_date, amount, func, del_days, 1)

# # Set pandas options to display all rows and columns
# pd.set_option('display.max_rows', None)  # Display all rows
# pd.set_option('display.max_columns', None)  # Display all columns
# pd.set_option('display.max_colwidth', None)  # Ensure that full content of each column is displayed

# # Print the generated DataFrame to console
# #print(ocel_event_log)

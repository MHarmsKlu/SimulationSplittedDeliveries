import pandas as pd
import random
import numpy as np
from datetime import datetime, timedelta


# Helper function to generate random timedelta in a realistic working day range
def generate_random_timedelta(min_days, max_days, min_hours=8, max_hours=17):
    """
    Generate a random timedelta with a random number of days between `min_days` and `max_days`
    and random hours between `min_hours` and `max_hours` (within working hours).
    """
    days = random.randint(min_days, max_days)
    hours = random.randint(min_hours, max_hours)
    minutes = random.randint(0, 59)
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
        timestamp = timestamp.replace(hour=8, minute=random.randint(0, 59))
    elif timestamp.hour >= 17:
        # Move the timestamp to the next working day at a random time between 08:00 and 17:00
        timestamp += timedelta(days=1)
        timestamp = timestamp.replace(hour=8, minute=random.randint(0, 59))

    return timestamp


def distribute_values(func, time_slots, target_sum, fixed_values=None):
    """
    Distributes values based on a given function and adapts to changed target values while maintaining the original function's shape.

    :param func: The mathematical function (e.g., lambda x: x**2)
    :param time_slots: Number of time slots
    :param target_sum: Target value to be reached
    :param fixed_values: Already fixed values {index: value}
    :return: List of calculated values
    """
    x_values = np.arange(1, time_slots + 1)
    y_values = np.array([func(x) for x in x_values])

    print("Initial function values:", y_values)

    if np.isscalar(y_values):
        y_values = np.full_like(x_values, y_values)

    is_decreasing = y_values[0] > y_values[-1]
    print("Is function decreasing:", is_decreasing)

    min_val, max_val = np.min(y_values), np.max(y_values)
    y_values = y_values - min_val + 1
    print("Shifted function values (positive):", y_values)

    normalized_y_values = y_values / np.sum(y_values)
    print("Normalized function values (sum=1):", normalized_y_values)
    print("Sum of normalized values:", np.sum(normalized_y_values))

    fixed_values = fixed_values or {}
    fixed_sum = sum(fixed_values.values())
    remaining_target = max(0, target_sum - fixed_sum)
    print("Fixed values:", fixed_values)
    print("Remaining target sum:", remaining_target)

    # Scale the normalized values based on the target sum
    scaled_y_values = np.round(normalized_y_values * target_sum).astype(int)
    print("Scaled function values before correction:", scaled_y_values)
    print("Sum of scaled values before rounding correction:", np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum)

    # Calculate the total sum of scaled values and the difference from target_sum
    total_sum = np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum
    diff = target_sum - total_sum
    print("Difference from target_sum:", diff)

    if diff != 0:
        # Adjust the last value to match the target sum exactly
        adjustable_indices = np.arange(len(scaled_y_values))[len(fixed_values):]
        sorted_adjustment_indices = adjustable_indices[np.argsort(-normalized_y_values[len(fixed_values):])]
        i = 0
        while diff != 0 and len(sorted_adjustment_indices) > 0:
            index = sorted_adjustment_indices[i % len(sorted_adjustment_indices)]
            scaled_y_values[index] += np.sign(diff)
            diff -= np.sign(diff)
            i += 1

    # Ensure all values are at least 1
    scaled_y_values = np.maximum(1, scaled_y_values)

    print("Adjusted scaled values:", scaled_y_values)
    print("Sum of scaled values after rounding correction:", np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum)

    if is_decreasing:
        scaled_y_values = np.sort(scaled_y_values)[::-1]
    print("Final sorted values:", scaled_y_values)

    result = [None] * time_slots
    for i in fixed_values:
        result[i - 1] = fixed_values[i]
    print("Result with fixed values:", result)

    for i in range(time_slots):
        if result[i] is None:
            result[i] = scaled_y_values[i]
    print("Final result:", result)
    print("Sum of final result:", sum(result))

    # Adjust the last entry to ensure the total sum is exactly target_sum
    result[-1] += target_sum - sum(result)
    print("Final adjusted result with corrected last entry:", result)
    print("Final sum after correction:", sum(result))

    return result


# Function to generate OCEL event log
def generate_ocel_event_log(start_date, amount, func, del_days):
    # Generate order_id for consistency across all activities
    order_id = f"order_{random.randint(1000, 9999)}"
    item_id = f"item_{random.randint(1000, 9999)}"

    # Adjust start date to ensure it's a weekday
    start_date = adjust_to_weekday(start_date)

    # Generate timestamps for each event based on the start date
    place_order_timestamp = start_date
    send_invoice_timestamp = place_order_timestamp + generate_random_timedelta(1, 3)  # 1-3 days for invoice
    receive_payment_timestamp = send_invoice_timestamp + generate_random_timedelta(1, 7)  # 1-7 days for payment

    # Distribute values for the amount to determine when to check availability
    check_availability_days = distribute_values(func, del_days, amount)

    # Create events for the log
    events = [
        {
            "event_id": "e1",
            "timestamp": place_order_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Place Order",
            "object_id": order_id,
            "object_type": "Order",
            "attributes": str({
                "amount": amount,
                "item_id": item_id
            })  # Ensure attributes are a string for proper display
        },
        {
            "event_id": "e2",
            "timestamp": send_invoice_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Send Invoice",
            "object_id": order_id,
            "object_type": "Order",
            "attributes": str({
                "invoice_amount": amount,
                "invoice_id": f"invoice_{random.randint(1000, 9999)}"
            })  # Ensure attributes are a string for proper display
        },
        {
            "event_id": "e3",
            "timestamp": receive_payment_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Receive Payment",
            "object_id": order_id,
            "object_type": "Order",
            "attributes": str({
                "payment_amount": amount,
                "payment_method": "Credit Card"
            })  # Ensure attributes are a string for proper display
        }
    ]

    # Now add the "Check Availability" events based on the distributed days
    current_timestamp = place_order_timestamp
    last_check_timestamp = current_timestamp
    previous_available_amount = 0  # Initially no amount has been used
    split_item_triggered = False  # Flag to track if Split Item has been triggered
    last_item_id = item_id  # Start with the initial item_id

    # Initialize the del_amount variable to track the cumulative available amount
    del_amount = 0  # Start with a cumulative amount of 0

    # Loop through all the `Check Availability` events
    for i, check_day in enumerate(check_availability_days):
        # Calculate the timestamp for the next "Check Availability"
        check_day = int(check_day)
        check_availability_timestamp = last_check_timestamp + timedelta(days=check_day)
        check_availability_timestamp = adjust_to_weekday(check_availability_timestamp)
        check_availability_timestamp += generate_random_timedelta(0, 1)  # Add a random time offset
        check_availability_timestamp = adjust_to_working_hours(check_availability_timestamp)

        # Add the current available amount to del_amount
        del_amount += check_availability_days[i]

        # Add the "Check Availability" event
        events.append({
            "event_id": f"e4_{i + 1}",
            "timestamp": check_availability_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Check Availability",
            "object_id": last_item_id,
            "object_type": "Item",
            "attributes": str({
                "availability_check_id": f"check_{i + 1}",
                "available_amount": check_availability_days[i]
            })
        })

        # Debugging print statement to track the process
        print(f"Checking availability for item {last_item_id} at {check_availability_timestamp}")
        print(f"Cumulative available amount (del_amount): {del_amount}")

        # Check if del_amount is still less than the total amount
        if del_amount < amount:
            # Trigger Split Item if the condition is met
            new_item_id_1 = f"item_{random.randint(1000, 9999)}"
            new_item_id_2 = f"item_{random.randint(1000, 9999)}"

            # Print debug for Split Item
            print(f"Split Item triggered! New item IDs: {new_item_id_1}, {new_item_id_2}")

            # Add the "Split Item" event (1 day after Check Availability)
            split_item_timestamp = check_availability_timestamp + timedelta(days=1)

            events.append({
                "event_id": f"e5_{i + 1}",
                "timestamp": split_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "activity": "Split Item",
                "object_id": last_item_id,
                "object_type": "Item",
                "attributes": str({
                    "new_item_id_1": new_item_id_1,
                    "new_item_id_2": new_item_id_2
                })
            })

            # Set the last_item_id to the first new item_id for future events
            last_item_id = new_item_id_1

        # Update the last timestamp for future events
        last_check_timestamp = check_availability_timestamp

        # After Split Item or Check Availability, execute the "Pick Item" activity
        if del_amount < amount:
            # If a Split Item occurred, use the new item_id_2 for Pick Item
            pick_item_timestamp = split_item_timestamp + timedelta(
                minutes=random.randint(15, 180))  # 15 mins to 3 hours
            pick_item_timestamp = adjust_to_working_hours(pick_item_timestamp)
            events.append({
                "event_id": f"e6_{i + 1}",
                "timestamp": pick_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "activity": "Pick Item",
                "object_id": new_item_id_2,  # Use the second item ID for the "Pick Item"
                "object_type": "Item",
                "attributes": str({
                    "pick_item_id": new_item_id_2
                })
            })
            print(f"Pick Item activity for {new_item_id_2} after Split Item at {pick_item_timestamp}")
        else:
            # If no Split Item occurred, use the item_id from Check Availability for Pick Item
            pick_item_timestamp = check_availability_timestamp + timedelta(
                minutes=random.randint(15, 180))  # 15 mins to 3 hours
            pick_item_timestamp = adjust_to_working_hours(pick_item_timestamp)
            events.append({
                "event_id": f"e6_{i + 1}",
                "timestamp": pick_item_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
                "activity": "Pick Item",
                "object_id": last_item_id,  # Use the item ID from Check Availability
                "object_type": "Item",
                "attributes": str({
                    "pick_item_id": last_item_id
                })
            })
            print(f"Pick Item activity for {last_item_id} after Check Availability at {pick_item_timestamp}")

        # After Pick Item, execute the "Pack Items" activity
        pack_items_timestamp = pick_item_timestamp + timedelta(minutes=random.randint(5, 60))  # 5 minutes to 1 hour
        pack_items_timestamp = adjust_to_working_hours(pack_items_timestamp)

        package_id = f"package_{random.randint(1000, 9999)}"  # Generate a random package ID

        # Add the "Pack Items" activity
        events.append({
            "event_id": f"e7_{i + 1}",
            "timestamp": pack_items_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Pack Items",
            "object_id": last_item_id,  # Same item ID as in Pick Item
            "object_type": "Item",
            "attributes": str({
                "package_id": package_id,  # New object package
                "item_id": last_item_id  # Same item as in Pick Item
            })
        })
        print(f"Pack Items activity for {last_item_id} with package {package_id} at {pack_items_timestamp}")

        # After Pack Items, execute the "Store Package" activity
        store_package_timestamp = pack_items_timestamp + timedelta(minutes=random.randint(5, 20))  # 5 to 20 minutes
        store_package_timestamp = adjust_to_working_hours(store_package_timestamp)
        # Add the "Store Package" activity
        events.append({
            "event_id": f"e8_{i + 1}",
            "timestamp": store_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Store Package",
            "object_id": package_id,  # Use the package_id created in Pack Items
            "object_type": "Package",
            "attributes": str({
                "package_id": package_id  # Same package_id
            })
        })
        print(f"Store Package activity for {package_id} at {store_package_timestamp}")

        # After Store Package, execute the "Load Package" activity
        load_package_timestamp = store_package_timestamp + timedelta(
            minutes=random.randint(20, 360))  # 20 minutes to 6 hours
        load_package_timestamp = adjust_to_working_hours(load_package_timestamp)
        # Add the "Load Package" activity
        events.append({
            "event_id": f"e9_{i + 1}",
            "timestamp": load_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Load Package",
            "object_id": package_id,  # Same package_id
            "object_type": "Package",
            "attributes": str({
                "package_id": package_id  # Same package_id
            })
        })
        print(f"Load Package activity for {package_id} at {load_package_timestamp}")

        # After Load Package, execute the "Deliver Package" activity
        deliver_package_timestamp = load_package_timestamp + timedelta(days=random.randint(3, 6))  # 3 to 6 days
        # Add the "Deliver Package" activity
        events.append({
            "event_id": f"e10_{i + 1}",
            "timestamp": deliver_package_timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "activity": "Deliver Package",
            "object_id": package_id,  # Same package_id
            "object_type": "Package",
            "attributes": str({
                "package_id": package_id  # Same package_id
            })
        })
        print(f"Deliver Package activity for {package_id} at {deliver_package_timestamp}")

    # Creating a DataFrame to hold the event log
    ocel_log = pd.DataFrame(events)

    return ocel_log


# Example usage of the function
start_date = datetime(2025, 4, 7, 8, 0, 0)  # Example start date (Monday, 8 AM)
amount = 150  # Example amount for the order
func = lambda x: x ** 2  # Example function for distributing the amount over time
del_days = 10  # Test with 10 days

# Generate the OCEL event log
ocel_event_log = generate_ocel_event_log(start_date, amount, func, del_days)

# Set pandas options to display all rows and columns
pd.set_option('display.max_rows', None)  # Display all rows
pd.set_option('display.max_columns', None)  # Display all columns
pd.set_option('display.max_colwidth', None)  # Ensure that full content of each column is displayed

# Print the generated DataFrame to console
print(ocel_event_log)

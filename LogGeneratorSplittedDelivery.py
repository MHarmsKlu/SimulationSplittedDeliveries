import pandas as pd
import numpy as np


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

    scaled_y_values = np.round(normalized_y_values * target_sum).astype(int)
    print("Scaled function values before correction:", scaled_y_values)
    print("Sum of scaled values before rounding correction:", np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum)

    diff = target_sum - (np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum)
    if diff != 0:
        adjustable_indices = np.arange(len(scaled_y_values))[len(fixed_values):]
        sorted_adjustment_indices = adjustable_indices[np.argsort(-normalized_y_values[len(fixed_values):])]
        i = 0
        while diff != 0 and len(sorted_adjustment_indices) > 0:
            index = sorted_adjustment_indices[
                i % len(sorted_adjustment_indices)]
            scaled_y_values[index] += np.sign(diff)
            diff -= np.sign(diff)
            i += 1

    scaled_y_values = np.maximum(1, scaled_y_values)
    print("Adjusted scaled values:", scaled_y_values)
    print("Sum of scaled values after rounding correction:", np.sum(scaled_y_values[len(fixed_values):]) + fixed_sum)

    if is_decreasing:
        scaled_y_values = np.sort(scaled_y_values)[::-1]
    print("Final sorted values:", scaled_y_values)

    result = [None] * time_slots
    for i in fixed_values:
        result[i-1] = fixed_values[i]
    print("Result with fixed values:", result)

    for i in range(time_slots):
        if result[i] is None:
            result[i] = scaled_y_values[i]
    print("Final result:", result)
    print("Sum of final result:", sum(result))

    return result



def generate_shipment_schedule(time_period, order_quantity, ship_func, time_slots_ship, seed=None):
    """
    Generates a shipment schedule ensuring a smooth linear distribution over the first 2/3 of the period.
    """
    if seed:
        np.random.seed(seed)

    shipment_schedule = {}
    remaining_quantity = order_quantity

    for day in range(1, time_slots_ship):
        expected_shipment = distribute_values(ship_func, time_slots_ship, order_quantity, fixed_values=shipment_schedule)
        # shipped_today = max(1, int(np.random.normal(expected_shipment[day], expected_shipment[day] * 0.1)))
        shipped_today = max(1, expected_shipment[day-1])
        shipped_today = min(shipped_today, remaining_quantity)
        shipment_schedule[day] = shipped_today
        remaining_quantity -= shipped_today

    # Ensure that any remaining quantity is shipped on the last shipment day
    if remaining_quantity > 0:
        shipment_schedule[time_slots_ship] = remaining_quantity

    # print(shipment_schedule)
    print("sum shipment schedule:", sum(shipment_schedule.values()))

    # Extend the schedule to cover all days in the time period
    extended_schedule = {day: 0 for day in range(1, time_period + 1)}
    shipment_days = list(shipment_schedule.keys())
    shipment_values = list(shipment_schedule.values())

    # Determine the distribution range
    if time_slots_ship < (2 / 3) * time_period:
        available_days = list(range(1, int(2 / 3 * time_period) + 1))
    else:
        available_days = list(range(1, time_period + 1))

    # Randomized but ordered distribution of shipment values over the time period
    selected_days = sorted(np.random.choice(available_days, len(shipment_days), replace=False))
    for original_day, new_day in zip(shipment_days, selected_days):
        extended_schedule[new_day] = shipment_schedule[original_day]

    print("Extended shipment schedule:", extended_schedule)
    return extended_schedule


def generate_dynamic_delivery_schedule(delivery_func, time_period, shipment_schedule, time_slots_del, seed=None):
    """
    Iteratively adjusts the delivery schedule based on shipped items, ensuring full delivery by the last day.
    """
    if seed:
        np.random.seed(seed)

    delivery_schedule = {day: 0 for day in range(1, time_period)}  # Initialize schedule with zeros
    remaining_shipped_quantity = sum(v for v in shipment_schedule.values())
    # print("remaining_shipped_quantity:", remaining_shipped_quantity)

    # Ensure the distribution of time_slots_del avoids the first 1/3 of the time period
    start_day = int(time_period / 3)
    if time_slots_del < (2 / 3) * time_period:
        marked_days = sorted(np.random.choice(range(start_day, time_period), time_slots_del, replace=False))
    else:
        marked_days = sorted(np.random.choice(range(start_day, time_period), time_slots_del, replace=False))

    # last_marked_day = marked_days.pop()  # Remove the last marked day from iteration
    # print("marked_days:", marked_days)
    # print("last_marked_day (excluded from iteration):", last_marked_day)

    # Iterate over the full time period except the last marked day
    for index, day in enumerate(marked_days):
        # print(f"Processing day {day}:")

        shipped_quantity = sum(v for k, v in shipment_schedule.items() if k <= day)
        # print(f"  Shipped quantity up to day {day}: {shipped_quantity}")

        filtered_schedule = {k: v for k, v in delivery_schedule.items() if v > 0}  # Remove zero values
        filtered_schedule = {new_key + 1: filtered_schedule[old_key] for new_key, old_key in enumerate(sorted(filtered_schedule))}
        # print(f"  Filtered schedule (non-zero values, reindexed): {filtered_schedule}")

        # print("delivery func:", delivery_func)
        # print("time slots del:", time_slots_del)
        # print("shipped quantity:", shipped_quantity)
        # print("filtered schedule:", filtered_schedule)
        expected_delivery = distribute_values(delivery_func, time_slots_del, shipped_quantity,
                                              fixed_values=filtered_schedule)
        # print(f"  Expected delivery distribution: {expected_delivery}")

        # delivered_today = max(1, int(np.random.normal(expected_delivery[index+1], expected_delivery[index+1] * 0.1)))
        delivered_today = max(1,
                              expected_delivery[index])
        # print(f"  Delivered delivery distribution: {delivered_today}")
        delivered_today = min(delivered_today, remaining_shipped_quantity)
        delivery_schedule[day] = delivered_today
        remaining_shipped_quantity -= delivered_today
        # print(f"  Remaining shipped quantity after day {day}: {remaining_shipped_quantity}")

    # Ensure that any remaining quantity is shipped on the last marked day
    if remaining_shipped_quantity > 0:
        # print(f"Assigning remaining quantity {remaining_shipped_quantity} to last marked day {last_marked_day}")
        delivery_schedule[marked_days[-1]] += remaining_shipped_quantity

    # print("Final delivery schedule:", delivery_schedule)
    # print("Sum of delivery schedule:", sum(delivery_schedule.values()))
    return delivery_schedule


def simulate_deliveries(order_quantity, time_period, start_date, ship_func, delivery_func, time_slots_ship, time_slots_del, seed=None):
    """
    Runs the shipment and delivery simulation.
    """

    if time_slots_ship > time_period or time_slots_del > time_period:
        raise ValueError(
            f"Error: time_slots_ship ({time_slots_ship}) or time_slots_del ({time_slots_del}) exceed time_period ({time_period})."
        )

    if seed:
        np.random.seed(seed)
    shipment_schedule = generate_shipment_schedule(time_period, order_quantity, ship_func, time_slots_ship, seed)
    delivery_schedule = generate_dynamic_delivery_schedule(delivery_func, time_period, shipment_schedule, time_slots_del, seed)
    events = [(1, 'Order Placed', start_date, order_quantity)]

    total_shipped = 0
    total_delivered = 0

    for day, qty in shipment_schedule.items():
        if qty > 0:
            total_shipped += qty
            events.append((1, 'Shipped', start_date + pd.Timedelta(days=day-1), qty))
    for day, qty in delivery_schedule.items():
        if qty > 0:
            total_delivered += qty
            events.append((1, 'Delivered', start_date + pd.Timedelta(days=day-1), qty))

    event_log = pd.DataFrame(events, columns=['process_id', 'event', 'timestamp', 'resource'])

    # Print full event log to console
    print("\nFull Event Log:")
    print(event_log.to_string(index=False))
    print(f"Total Shipped: {total_shipped}")
    print(f"Total Delivered: {total_delivered}")

    return event_log.sort_values(by=['timestamp', 'event'])


order_quantity = 100
time_period = 30
time_slots_ship = 7
time_slots_del = 10
start_date = pd.to_datetime("2025-01-01")


func_ship = lambda x: 2
func_exp = lambda x: x ** 2

event_log = simulate_deliveries(order_quantity, time_period, start_date,
                                ship_func=func_ship,
                                delivery_func=func_exp,
                                time_slots_ship=time_slots_ship,
                                time_slots_del=time_slots_del,
                                seed=42)

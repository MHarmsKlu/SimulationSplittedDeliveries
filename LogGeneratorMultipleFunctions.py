import pandas as pd
import numpy as np
import math


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


def generate_delivery_schedule(time_period, order_quantity, del_func, time_slots_del, day_func=None, random=True,
                               seed=None):
    """
    Generates a delivery schedule ensuring a smooth linear distribution over the first 2/3 of the period.
    """
    if seed:
        np.random.seed(seed)

    delivery_schedule = {}
    remaining_quantity = order_quantity

    if not day_func:
        for day in range(1, time_slots_del):
            expected_delivery = distribute_values(del_func, time_slots_del, order_quantity,
                                                  fixed_values=delivery_schedule)
            # shipped_today = max(1, int(np.random.normal(expected_shipment[day], expected_shipment[day] * 0.1)))
            shipped_today = max(1, expected_delivery[day - 1])
            shipped_today = min(shipped_today, remaining_quantity)
            delivery_schedule[day] = shipped_today
            remaining_quantity -= shipped_today

        # Ensure that any remaining quantity is shipped on the last shipment day
        if remaining_quantity > 0:
            delivery_schedule[time_slots_del] = remaining_quantity

        # print(shipment_schedule)
        print("sum shipment schedule:", sum(delivery_schedule.values()))

        # Extend the schedule to cover all days in the time period
        extended_schedule = {day: 0 for day in range(1, time_period + 1)}
        shipment_days = list(delivery_schedule.keys())
        shipment_values = list(delivery_schedule.values())

        # Determine the distribution range
        available_days = list(range(1, time_period + 1))

        # Randomized but ordered distribution of shipment values over the time period
        selected_days = sorted(np.random.choice(available_days, len(shipment_days), replace=False))
        for original_day, new_day in zip(shipment_days, selected_days):
            extended_schedule[new_day] = delivery_schedule[original_day]
    else:
        if random:
            points = sorted(np.random.choice(range(1, order_quantity), time_slots_del - 1, replace=False))
            delivery_schedule = [b - a for a, b in zip([0] + points, points + [order_quantity])]
            print(delivery_schedule)
            print("sum shipment schedule:", sum(delivery_schedule))
        else:
            for day in range(1, time_slots_del):
                expected_delivery = distribute_values(del_func, time_slots_del, order_quantity,
                                                      fixed_values=delivery_schedule)
                # shipped_today = max(1, int(np.random.normal(expected_shipment[day], expected_shipment[day] * 0.1)))
                shipped_today = max(1, expected_delivery[day - 1])
                shipped_today = min(shipped_today, remaining_quantity)
                delivery_schedule[day] = shipped_today
                remaining_quantity -= shipped_today

            # Ensure that any remaining quantity is shipped on the last shipment day
            if remaining_quantity > 0:
                delivery_schedule[time_slots_del] = remaining_quantity

            delivery_schedule = delivery_schedule.values()

        days = np.arange(1, time_period + 1)
        densities = np.array([day_func(day) for day in days])

        # If there are negative values, shift the entire distribution upwards
        min_density = densities.min()
        if min_density < 0:
            densities = densities - min_density  # Shift to positiv values

        if densities.sum() == 0:
            raise ValueError("All probability values are zero. Adjust the lambda function.")

        probabilities = densities / densities.sum()
        selected_days = np.random.choice(days, size=time_slots_del, replace=False, p=probabilities)
        schedule = [1 if day in selected_days else 0 for day in days]

        print("Extended shipment schedule:", schedule)

        extended_schedule = {}
        value_iter = iter(delivery_schedule)

        for idx, val in enumerate(schedule, start=1):
            if val == 1:
                extended_schedule[idx] = next(value_iter)
            else:
                extended_schedule[idx] = 0

    print(extended_schedule)
    return extended_schedule


def simulate_deliveries(order_quantity, time_period, start_date, del_func, time_slots_del, pid, day_func=None,
                        random=True, seed=None):
    """
    Runs the shipment and delivery simulation.
    """

    if time_slots_del > time_period:
        raise ValueError(
            f"Error: time_slots_ship ({time_slots_del}) exceed time_period ({time_period})."
        )

    if seed:
        np.random.seed(seed)
    delivery_schedule = generate_delivery_schedule(time_period, order_quantity, del_func, time_slots_del, day_func,
                                                   random, seed)
    events = [(pid, 'Order Placed', start_date, order_quantity)]

    total_delivery = 0

    for day, qty in delivery_schedule.items():
        if qty > 0:
            total_delivery += qty
            events.append((pid, 'Delivery', start_date + pd.Timedelta(days=day), qty))

    event_log = pd.DataFrame(events, columns=['process_id', 'event', 'timestamp', 'resource'])

    # Print full event log to console
    print("\nFull Event Log:")
    print(event_log.to_string(index=False))
    print(f"Total Shipped: {total_delivery}")

    return event_log.sort_values(by=['timestamp', 'event'])


order_quantity = 100
time_period = 30
time_slots_del = 7
start_date = pd.to_datetime("2025-01-01")
event_log = pd.DataFrame()

# func_ship = lambda x: x**2
index = 1
# 1:negative square function, 2:linear function, 3:square function, 4: square function with negative startpoint, 5: log function, 6: log10 function, 7: normal distribution, 8: equal distribution, 9: right skewed function, 10. left skewed function, 11: root function, 12: sinus function
# func_list = [lambda x: 20 - x**2, lambda x: 2, lambda x: x**2, lambda x: - 20 + 2*x, lambda x: math.log(x), lambda x: math.log10(x), lambda x: (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x**2), lambda x: 1 if 0 <= x <= 1 else 0, lambda x: math.exp(-x) if x >= 0 else 0, lambda x: math.exp(x) if x <= 0 else 0, lambda x: math.sqrt(x) if x >= 0 else None, lambda x: math.sin(x)]
func_list = [lambda x: 2, lambda x: x ** 2, lambda x: math.log(x)]

for func_1 in func_list:
    for func_2 in func_list:
        new_event_log = simulate_deliveries(order_quantity, time_period, start_date,
                                            del_func=func_1,
                                            time_slots_del=time_slots_del,
                                            pid=index,
                                            day_func=func_2,
                                            random=False,
                                            seed=42)
        event_log = pd.concat([event_log, new_event_log], axis=0)
        start_date = start_date + pd.Timedelta(days=10)
        index += 1

print(event_log.to_string(index=False))

event_log.to_csv("eventlog.csv", index= False)

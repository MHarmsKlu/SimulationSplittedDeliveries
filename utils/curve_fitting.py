import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error

# Sample Data
x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
y = np.array([2.1, 2.9, 3.7, 5.1, 6.5, 8.1, 10.3, 12.5, 15.1, 18.0])

# Define possible models
def linear(x, a, b): return a * x + b
def quadratic(x, a, b, c): return a * x**2 + b * x + c
def exponential(x, a, b): return a * np.exp(b * x)
def logarithmic(x, a, b): return a * np.log(x) + b
def power_law(x, a, b): return a * x**b

models = {
    "Linear": linear,
    "Quadratic": quadratic,
    "Exponential": exponential,
    "Logarithmic": logarithmic,
    "Power Law": power_law
}

# Fit models and compare performance
best_model = None
best_score = float('-inf')
results = {}

for name, func in models.items():
    try:
        params, _ = curve_fit(func, x, y, maxfev=5000)
        y_pred = func(x, *params)
        r2 = r2_score(y, y_pred)
        rmse = mean_squared_error(y, y_pred, squared=False)

        results[name] = {"R²": r2, "RMSE": rmse, "Params": params}

        if r2 > best_score:
            best_score = r2
            best_model = (name, func, params)
    
    except Exception as e:
        print(f"Skipping {name}: {e}")

# Print results
for name, res in results.items():
    print(f"{name}: R² = {res['R²']:.4f}, RMSE = {res['RMSE']:.4f}")

# Best model selection
best_name, best_func, best_params = best_model
print(f"\nBest Model: {best_name} (R² = {best_score:.4f})")

# Plot best model
x_fit = np.linspace(min(x), max(x), 100)
y_fit = best_func(x_fit, *best_params)

plt.scatter(x, y, label="Data")
plt.plot(x_fit, y_fit, label=f"Best Fit: {best_name}", color='red')
plt.legend()
plt.show()
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gamma
from scipy.integrate import quad

# Parameters
a = 3.0
loc = 0.0
scale = 2.0
dist = gamma

# X range for plot
x = np.linspace(0, 20, 500)
pdf_vals = dist.pdf(x, a, loc=loc, scale=scale)

# Truncation bounds
x_min = 2
x_max = 10

# Functions for integration
def pdf(x):
    return dist.pdf(x, a, loc=loc, scale=scale)

def x_pdf(x):
    return x * pdf(x)

# Truncated mean
numerator, _ = quad(x_pdf, x_min, x_max)
denominator, _ = quad(pdf, x_min, x_max)
truncated_mean = numerator / denominator

# Full mean
full_mean = dist.mean(a, loc=loc, scale=scale)

# Plot
plt.figure(figsize=(10, 6))
plt.plot(x, pdf_vals, label='Gamma PDF', color='blue')

# Highlight truncated area
x_fill = np.linspace(x_min, x_max, 300)
plt.fill_between(x_fill, pdf(x_fill), color='orange', alpha=0.5, label='Truncation Range')

# Mean lines
plt.axvline(full_mean, color='green', linestyle='--', label=f'Full Mean = {full_mean:.2f}')
plt.axvline(truncated_mean, color='red', linestyle='--', label=f'Truncated Mean = {truncated_mean:.2f}')

plt.title('Gamma Distribution: Full vs Truncated Mean')
plt.xlabel('x')
plt.ylabel('PDF')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import (
    gengamma, norm, laplace, t, cauchy, beta, uniform, gumbel_r
)
from scipy.optimize import curve_fit
from sklearn.metrics import r2_score, mean_squared_error
from scipy.integrate import quad

# def gaussian_model(x, amplitude, mean, std_dev): return amplitude * norm.pdf(x, loc=mean, scale=std_dev)
# def gamma_model(x, amplitude, a, loc, scale): return amplitude * gamma.pdf(x, a, loc=loc, scale=scale)
# #def exponential_model(x, amplitude, loc, scale):return amplitude * expon.pdf(x, loc=loc, scale=scale)
# def laplace_model(x, amplitude, loc, scale): return amplitude * laplace.pdf(x, loc=loc, scale=scale)
# def lognormal_model(x, amplitude, s, loc, scale): return amplitude * lognorm.pdf(x, s, loc=loc, scale=scale)
# def uniform_model(x, amplitude, loc, scale): return amplitude * uniform.pdf(x, loc=loc, scale=scale)

# models = {
#     "Normal": gaussian_model,
#     "Gamma": gamma_model,
#     "Laplace": laplace_model,
#     "Longnormal": lognormal_model,
#     "Uniform": uniform_model
# }

distributions = {
    "Generalized Gamma": (gengamma, 2),
    "Normal": (norm, 0),
    "Laplace": (laplace, 0),
    "Student t": (t, 1),
    "Cauchy": (cauchy, 0),
    "Beta": (beta, 2),
    "Uniform": (uniform, 0),
    "Gumbel": (gumbel_r, 0)
}

def get_model(dist, num_shapes):
    def model(x, amplitude, *params):
        shape_params = params[:num_shapes]
        loc = params[num_shapes]
        scale = params[num_shapes + 1]
        return amplitude * dist.pdf(x, *shape_params, loc=loc, scale=scale)
    return model

def fit_distribution(x,y):
    results = {}
    best_model = None
    best_r2 = -np.inf

    for name, (dist, num_shapes) in distributions.items():
        try:
            model = get_model(dist, num_shapes)
            p0 = [1.0] + [1.5] * num_shapes + [0.0, 1.0]  # initial guess

            params, _ = curve_fit(model, x, y, p0=p0, maxfev=1000000)
            y_pred = model(x, *params)

            r2 = r2_score(y, y_pred)
            rmse = mean_squared_error(y, y_pred)

            results[name] = {
                "R²": r2,
                "RMSE": rmse,
                "Params": params
            }

            if r2 > best_r2:
                best_r2 = r2
                best_model = (name, params)

        except Exception as e:
            results[name] = {"Error": str(e)}

    # Print results
    # for name, res in results.items():
    #     print(f"{name}: R² = {res['R²']:.4f}, RMSE = {res['RMSE']:.4f}")

    # Best model selection
    return expected_value_over_range_cdf(best_model[0], best_model[1], np.min(x), np.max(x))
    
def get_expected_value(dist_name, params):
    dist_obj, num_shape_params = distributions[dist_name]
    shape_params = params[1 : 1 + num_shape_params]
    loc = params[1 + num_shape_params]
    scale = params[2 + num_shape_params]
    try:
        return dist_obj.mean(*shape_params, loc=loc, scale=scale)
    except Exception as e:
        return f"Mean undefined or error: {e}"

def expected_value_over_range(dist_name, params, x_min, x_max):
    dist_obj, num_shape_params = distributions[dist_name]
    shape_params = params[1 : 1 + num_shape_params]
    loc = params[1 + num_shape_params]
    scale = params[2 + num_shape_params]
    # Define the scaled PDF
    def pdf(x):
        return dist_obj.pdf(x, *shape_params, loc=loc, scale=scale)
    
    # Define x * PDF(x)
    def x_pdf(x):
        return x * pdf(x)
    
    # Integrate x * f(x) and f(x) over [x_min, x_max]
    numerator, _ = quad(x_pdf, x_min, x_max)
    denominator, _ = quad(pdf, x_min, x_max)
    
    return numerator / denominator if denominator > 0 else float('nan')

def expected_value_over_range_cdf(dist_name, params, x_min, x_max):
    """
    Computes E[X | X ∈ [x_min, x_max]] using:
    E[X | X ∈ [a, b]] = 1 / (F(b) - F(a)) * ∫_a^b x f(x) dx
    """
    dist_obj, num_shape_params = distributions[dist_name]
    shape_params = params[1 : 1 + num_shape_params]
    loc = params[1 + num_shape_params]
    scale = params[2 + num_shape_params]
    # Define x * PDF(x)
    def x_pdf(x):
        return x * dist_obj.pdf(x, *shape_params, loc=loc, scale=scale)
    
    # CDF values at bounds
    F_max = dist_obj.cdf(x_max, *shape_params, loc=loc, scale=scale)
    F_min = dist_obj.cdf(x_min, *shape_params, loc=loc, scale=scale)
    denominator = F_max - F_min

    # Handle invalid cases
    if denominator == 0:
        return float('nan')

    # Numerator: ∫ x f(x) dx from x_min to x_max
    numerator, _ = quad(x_pdf, x_min, x_max)

    return numerator / denominator
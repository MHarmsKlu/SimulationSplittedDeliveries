from matplotlib import pyplot as plt

x = [10, 15, 17, 22, 24, 26, 32, 39, 42, 45, 51, 54, 60, 66, 75, 82, 85, 92, 93]
y = [105, 87, 80, 78, 77, 77, 77, 77, 76, 76, 76, 76, 76, 76, 76, 76, 76, 76, 76]

plt.scatter(x, y, label="Data")

plt.legend()
plt.show()  
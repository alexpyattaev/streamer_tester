import numpy as np
import sys
from mpl_toolkits.mplot3d import Axes3D  # registers 3D projection
import matplotlib.pyplot as plt

data = np.genfromtxt("datapoints.csv", delimiter=" ")
x, y, z = data[:, 0], data[:, 1], data[:, 2]

# combine x and y into keys
keys = np.column_stack((x, y))
# find unique pairs and mapping
uniq, inv = np.unique(keys, axis=0, return_inverse=True)

# average z per unique pair
z = np.bincount(inv, weights=z) / np.bincount(inv)

x, y = uniq[:, 0], uniq[:, 1]


fig = plt.figure()
ax = fig.add_subplot(111, projection="3d")

# sc = ax.scatter(np.array(x, dtype=int), np.array(y/1000,dtype=int), np.array(z/1000,dtype=int), c=z, cmap='viridis')
sc = ax.plot_trisurf(x, y, z, cmap="viridis", edgecolor="none")
title = "_".join(sys.argv[1:])
plt.title(title)

plt.xlabel("latency, ms")
plt.ylabel("stake, Ksol")
ax.set_zlabel("TPS")
cb = fig.colorbar(sc, ax=ax, shrink=0.5, aspect=10, location="left")
cb.set_label("TPS")  # colorbar label

plt.savefig(f"plot_{title}.png")

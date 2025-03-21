import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np

SECONDARY_CHARACTERISTIC = 'Files Changed'   # replace with 'Files Changed', 'Total Comments', 'LOC Changed' etc

df = pd.read_csv("data/pull_requests_filtered.csv")

# Separate merged and closed PRs
merged_prs = df[df['State'] == 'merged']
closed_prs = df[df['State'] == 'closed']
print(len(merged_prs))
print(len(closed_prs))

merged_decision_times = merged_prs['Decision Time']
closed_decision_times = closed_prs['Decision Time']

# For the secondary characteristic, we'll keep using all PRs
decision_times = df['Decision Time']
secondary_characteristic = df[SECONDARY_CHARACTERISTIC]

bins = [0, 3, 7, 30, np.percentile(df['Decision Time'], 98)]

bin_indices = np.digitize(decision_times, bins)  # assign each PR to its bin index

secondary_characteristic_by_bin = [
    secondary_characteristic[bin_indices == i]
    for i in range(1, len(bins))
]
capped_secondary_characteristic_by_bin = [
    np.clip(bin_data, None, np.percentile(secondary_characteristic, 98))    # stop outliers making axes huge by taking 98th percentile cutoff
    for bin_data in secondary_characteristic_by_bin
]

plt.figure(figsize=(12, 8))
fig, ax = plt.subplots(figsize=(12, 8))

hist_closed, bin_edges, _ = ax.hist(
    closed_decision_times, bins=bins, edgecolor='black', alpha=0.7, 
    label='Closed PRs', align='mid', color='#B22222'  # Firebrick
)

hist_merged, _, _ = ax.hist(
    merged_decision_times, bins=bins, edgecolor='black', alpha=0.7,
    label='Merged PRs', align='mid', color='#4682B4',  # Steel Blue
    bottom=hist_closed  # Stack on top of closed PRs
)

plt.xscale('log')

# Create secondary y-axis for the box plots
ax2 = ax.twinx()
ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

log_bins = np.log10(bins[1:])
log_bins = np.insert(log_bins, 0, [0])

# Add box plots for each bin
bin_centers = [10 ** (((log_bins[i] + log_bins[i + 1])) / 2) for i in range(len(log_bins) - 1)]  # center positions for box plots
for i, secondary_characteristic_data in enumerate(capped_secondary_characteristic_by_bin):
    ax2.boxplot(
        secondary_characteristic_data,
        positions=[bin_centers[i]],  # place the box plot at the bin center
        widths=(bins[i + 1] - bins[i]) * 0.2,  # adjust width to match bin size
        vert=True,
        patch_artist=True,
        boxprops=dict(facecolor="lightblue", color="black"),
    )

ax.set_xticks([1] + bins[1:], [str(int(b)) for b in bins])      # log scale, so use 1 as first value as log(1) = 0 for first tick

plt.title('Distribution of PR Decision Times')
ax.set_xlabel('Decision Time (days)')
ax.set_ylabel('Number of PRs')
ax2.set_ylabel(SECONDARY_CHARACTERISTIC)
plt.grid(visible=True, linestyle='--', alpha=0.5)

# Add legend
ax.legend(loc='upper right')

# plt.savefig(f'plot-images/decision_time_with_merged_closed_prs.png')
plt.show()
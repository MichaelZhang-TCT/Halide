import argparse
from pathlib import Path
import pdb
import sh
import os
import math

class Result:
  def __init__(self, actual, predicted):
    self.actual = actual
    self.predicted = predicted
    if actual != 0:
      self.ratio = 100 * abs(predicted - actual) / actual
    else:
      if predicted == 0:
        self.ratio = 0
      else:
        self.ratio = math.inf

  def __str__(self):
    return "{:>14.2f} {:>14.2f} {:>7.2f}".format(self.actual, self.predicted, self.ratio)

class IntResult(Result):
  def __init__(self, actual, predicted):
    super().__init__(actual, predicted)

  def __str__(self):
    return "{:>14d} {:>14d} {:>7.2f}".format(int(self.actual), int(self.predicted), self.ratio)


class Sample:
  def __init__(self, path, metrics_path, features_path):
    self.path = path
    self.metrics = self.parse_formatted(metrics_path)
    self.features = self.parse_formatted(features_path)
    self.results = {}

    self.comparisons = {}
    self.comparisons["global load transactions"] = self.global_load_transactions
    self.comparisons["global store transactions"] = self.global_store_transactions
    self.comparisons["global load efficiency"] = self.global_load_efficiency
    self.comparisons["global store efficiency"] = self.global_store_efficiency

    self.compare_metrics_and_features()

  def parse_formatted(self, filename):
    result = {}
    with open(filename) as file:
      for line in file:
        stage, key, value = line.split()
        if not stage in result:
          result[stage] = {}

        result[stage][key] = float(value)

    return result

  def global_load_efficiency(self, metrics, features):
    actual = metrics["gld_efficiency"]
    predicted = features["global_mem_load_efficiency"] * 100

    if actual == 0:
      actual = 100

    return Result(actual, predicted)

  def global_store_efficiency(self, metrics, features):
    actual = metrics["gst_efficiency"]
    predicted = features["global_mem_store_efficiency"] * 100

    if actual == 0:
      actual = 100

    return Result(actual, predicted)

  def global_load_transactions(self, metrics, features):
    actual = metrics["gld_transactions"]
    predicted = features["num_global_mem_loads_per_block"] * features["num_blocks"]
    return IntResult(actual, predicted)

  def global_store_transactions(self, metrics, features):
    actual = metrics["gst_transactions"]
    predicted = features["num_global_mem_stores_per_block"] * features["num_blocks"]
    return IntResult(actual, predicted)

  def compare_metrics_and_features(self):
    for stage in self.features:
      self.results[stage] = {}
      for label in self.comparisons:
        self.results[stage][label] = self.comparisons[label](self.metrics[stage], self.features[stage])

  def max_ratio(self):
    ratios = []
    for stage in self.results:
      for label in self.results[stage]:
        ratios.append(abs(self.results[stage][label].ratio))

    return max(ratios)

  def __str__(self):
    out = "{}/autoschedule_command.txt\n".format(self.path.parent)
    first = True
    for stage in self.results:

      width = max([len(k) for k in self.comparisons.keys()])

      if first:
        first = False
        out += "{:{width}} {:>14} {:>14} {:>7}\n".format(stage, "Actual", "Predicted", "Ratio", width=width + 2)
      else:
        out += "{:{width}}\n".format(stage, width=width + 2)

      for label in self.results[stage]:
        result = self.results[stage][label]
        out += "  {:{width}} {}\n".format(label, str(self.results[stage][label]), width=width)

    return out

def compare_metrics_and_features(outliers_filename, N):
  with open(outliers_filename) as file:
    all_sample_paths = [Path(line.rstrip().split(", ")[0]) for line in file]

  sample_paths = all_sample_paths
  if N > 0:
    sample_paths = all_sample_paths[0:N]
    sample_paths.extend(all_sample_paths[-N:])

  samples = []

  for sample_path in sample_paths:
    metrics_path = Path("{}/formatted_metrics.txt".format(sample_path.parent))
    features_path = Path("{}/formatted_features.txt".format(sample_path.parent))

    if not metrics_path.is_file():
      print("Metrics file not found: {}".format(metrics_path))
      continue

    if not features_path.is_file():
      print("Features file not found: {}".format(features_path))
      continue

    samples.append(Sample(sample_path, metrics_path, features_path))

  samples.sort(key=lambda s: s.max_ratio())
  for s in samples:
    print(s)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--outliers", type=str, required=True)
  parser.add_argument("--N", type=int, required=True)

  args = parser.parse_args()

  compare_metrics_and_features(Path(args.outliers), args.N)
package io.archguard.api;

public enum Severity {
  INFO,
  WARNING,
  ERROR;

  public boolean atLeast(Severity threshold) {
    return ordinal() >= threshold.ordinal();
  }
}

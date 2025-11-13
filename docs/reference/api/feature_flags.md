# Feature flag reference

-----

::: dda.feature_flags.manager.FeatureFlagManager
    options:
      members:
      - enabled

::: dda.feature_flags.manager.FeatureFlagEvaluationResult
    options:
      members:
      - value
      - defaulted
      - error

::: dda.feature_flags.client.DatadogFeatureFlag
    options:
      members:
      - get_flag_value

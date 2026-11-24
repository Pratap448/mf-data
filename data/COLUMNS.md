# fund_metrics columns

Suffix `_Ny` = measured over the last N years to the last month-end (monthly returns unless config says otherwise).
Prefix `cat_` = measured against the category-average index instead of the benchmark.
`_rank/_of/_pctile/_quartile` = position within the peer group (Growth options only; 1 = best).

| column | meaning |
|---|---|
| as_of |  |
| amfi_code |  |
| scheme_name |  |
| amc |  |
| scheme_type |  |
| sebi_category |  |
| category_group |  |
| plan |  |
| option |  |
| peer_group |  |
| benchmark_index |  |
| isin_growth |  |
| isin_reinv |  |
| ter_total | expense ratio % |
| ter_base | expense ratio % |
| ter_brokerage | expense ratio % |
| ter_transaction | expense ratio % |
| ter_statutory | expense ratio % |
| ter_date | expense ratio % |
| first_nav_date |  |
| last_nav_date |  |
| last_nav |  |
| ret_1m | trailing point-to-point return %, CAGR above 1 year |
| ret_3m | trailing point-to-point return %, CAGR above 1 year |
| ret_6m | trailing point-to-point return %, CAGR above 1 year |
| ret_ytd | trailing point-to-point return %, CAGR above 1 year |
| ret_1y | trailing point-to-point return %, CAGR above 1 year |
| ret_2y | trailing point-to-point return %, CAGR above 1 year |
| ret_3y | trailing point-to-point return %, CAGR above 1 year |
| ret_5y | trailing point-to-point return %, CAGR above 1 year |
| ret_7y | trailing point-to-point return %, CAGR above 1 year |
| ret_10y | trailing point-to-point return %, CAGR above 1 year |
| ret_si | trailing point-to-point return %, CAGR above 1 year |
| cy_2016 | calendar-year return % |
| cy_2017 | calendar-year return % |
| cy_2018 | calendar-year return % |
| cy_2019 | calendar-year return % |
| cy_2020 | calendar-year return % |
| cy_2021 | calendar-year return % |
| cy_2022 | calendar-year return % |
| cy_2023 | calendar-year return % |
| cy_2024 | calendar-year return % |
| cy_2025 | calendar-year return % |
| obs_1y |  |
| ann_return_1y | annualised return % |
| std_dev_1y | annualised standard deviation % |
| downside_dev_1y | annualised downside deviation % (below risk-free) |
| sharpe_1y | Sharpe ratio |
| sortino_1y | Sortino ratio |
| skewness_1y | skewness |
| kurtosis_1y | excess kurtosis |
| var_95_1y | 95% value-at-risk per period % |
| cvar_95_1y | 95% expected shortfall per period % |
| omega_1y | Omega ratio |
| pct_positive_periods_1y |  |
| best_period_1y |  |
| worst_period_1y |  |
| mean_excess_per_period_1y |  |
| max_drawdown_1y | max drawdown % (daily) |
| dd_days_to_recover_1y |  |
| longest_underwater_days_1y | longest period below a previous peak (days) |
| ulcer_index_1y | Ulcer index |
| current_drawdown_1y | drawdown from peak at window end % |
| calmar_1y | annualised return / max drawdown |
| cat_obs_rel_1y |  |
| cat_beta_1y | beta |
| cat_alpha_1y | Jensen's alpha % p.a. |
| cat_r_squared_1y | R-squared % |
| cat_correlation_1y | correlation |
| cat_tracking_error_1y | tracking error % p.a. |
| cat_active_return_1y | same as excess_return |
| cat_information_ratio_1y | information ratio |
| cat_treynor_1y | Treynor ratio % |
| cat_m2_1y | Modigliani M-squared % |
| cat_up_capture_1y | up-market capture % (geometric) |
| cat_down_capture_1y | down-market capture % (geometric) |
| cat_capture_ratio_1y | up capture / down capture |
| cat_up_capture_arith_1y | up-market capture % (geometric) |
| cat_down_capture_arith_1y | down-market capture % (geometric) |
| cat_batting_avg_1y | % of periods beating the benchmark |
| cat_up_batting_avg_1y |  |
| cat_down_batting_avg_1y |  |
| cat_bm_ann_return_1y | benchmark value of the same measure |
| cat_bm_std_dev_1y | benchmark value of the same measure |
| cat_excess_return_1y | annualised return minus benchmark's |
| obs_3y |  |
| ann_return_3y | annualised return % |
| std_dev_3y | annualised standard deviation % |
| downside_dev_3y | annualised downside deviation % (below risk-free) |
| sharpe_3y | Sharpe ratio |
| sortino_3y | Sortino ratio |
| skewness_3y | skewness |
| kurtosis_3y | excess kurtosis |
| var_95_3y | 95% value-at-risk per period % |
| cvar_95_3y | 95% expected shortfall per period % |
| omega_3y | Omega ratio |
| pct_positive_periods_3y |  |
| best_period_3y |  |
| worst_period_3y |  |
| mean_excess_per_period_3y |  |
| max_drawdown_3y | max drawdown % (daily) |
| dd_days_to_recover_3y |  |
| longest_underwater_days_3y | longest period below a previous peak (days) |
| ulcer_index_3y | Ulcer index |
| current_drawdown_3y | drawdown from peak at window end % |
| calmar_3y | annualised return / max drawdown |
| cat_obs_rel_3y |  |
| cat_beta_3y | beta |
| cat_alpha_3y | Jensen's alpha % p.a. |
| cat_r_squared_3y | R-squared % |
| cat_correlation_3y | correlation |
| cat_tracking_error_3y | tracking error % p.a. |
| cat_active_return_3y | same as excess_return |
| cat_information_ratio_3y | information ratio |
| cat_treynor_3y | Treynor ratio % |
| cat_m2_3y | Modigliani M-squared % |
| cat_up_capture_3y | up-market capture % (geometric) |
| cat_down_capture_3y | down-market capture % (geometric) |
| cat_capture_ratio_3y | up capture / down capture |
| cat_up_capture_arith_3y | up-market capture % (geometric) |
| cat_down_capture_arith_3y | down-market capture % (geometric) |
| cat_batting_avg_3y | % of periods beating the benchmark |
| cat_up_batting_avg_3y |  |
| cat_down_batting_avg_3y |  |
| cat_bm_ann_return_3y | benchmark value of the same measure |
| cat_bm_std_dev_3y | benchmark value of the same measure |
| cat_excess_return_3y | annualised return minus benchmark's |
| obs_5y |  |
| ann_return_5y | annualised return % |
| std_dev_5y | annualised standard deviation % |
| downside_dev_5y | annualised downside deviation % (below risk-free) |
| sharpe_5y | Sharpe ratio |
| sortino_5y | Sortino ratio |
| skewness_5y | skewness |
| kurtosis_5y | excess kurtosis |
| var_95_5y | 95% value-at-risk per period % |
| cvar_95_5y | 95% expected shortfall per period % |
| omega_5y | Omega ratio |
| pct_positive_periods_5y |  |
| best_period_5y |  |
| worst_period_5y |  |
| mean_excess_per_period_5y |  |
| max_drawdown_5y | max drawdown % (daily) |
| dd_days_to_recover_5y |  |
| longest_underwater_days_5y | longest period below a previous peak (days) |
| ulcer_index_5y | Ulcer index |
| current_drawdown_5y | drawdown from peak at window end % |
| calmar_5y | annualised return / max drawdown |
| cat_obs_rel_5y |  |
| cat_beta_5y | beta |
| cat_alpha_5y | Jensen's alpha % p.a. |
| cat_r_squared_5y | R-squared % |
| cat_correlation_5y | correlation |
| cat_tracking_error_5y | tracking error % p.a. |
| cat_active_return_5y | same as excess_return |
| cat_information_ratio_5y | information ratio |
| cat_treynor_5y | Treynor ratio % |
| cat_m2_5y | Modigliani M-squared % |
| cat_up_capture_5y | up-market capture % (geometric) |
| cat_down_capture_5y | down-market capture % (geometric) |
| cat_capture_ratio_5y | up capture / down capture |
| cat_up_capture_arith_5y | up-market capture % (geometric) |
| cat_down_capture_arith_5y | down-market capture % (geometric) |
| cat_batting_avg_5y | % of periods beating the benchmark |
| cat_up_batting_avg_5y |  |
| cat_down_batting_avg_5y |  |
| cat_bm_ann_return_5y | benchmark value of the same measure |
| cat_bm_std_dev_5y | benchmark value of the same measure |
| cat_excess_return_5y | annualised return minus benchmark's |
| obs_7y |  |
| ann_return_7y | annualised return % |
| std_dev_7y | annualised standard deviation % |
| downside_dev_7y | annualised downside deviation % (below risk-free) |
| sharpe_7y | Sharpe ratio |
| sortino_7y | Sortino ratio |
| skewness_7y | skewness |
| kurtosis_7y | excess kurtosis |
| var_95_7y | 95% value-at-risk per period % |
| cvar_95_7y | 95% expected shortfall per period % |
| omega_7y | Omega ratio |
| pct_positive_periods_7y |  |
| best_period_7y |  |
| worst_period_7y |  |
| mean_excess_per_period_7y |  |
| max_drawdown_7y | max drawdown % (daily) |
| dd_days_to_recover_7y |  |
| longest_underwater_days_7y | longest period below a previous peak (days) |
| ulcer_index_7y | Ulcer index |
| current_drawdown_7y | drawdown from peak at window end % |
| calmar_7y | annualised return / max drawdown |
| cat_obs_rel_7y |  |
| cat_beta_7y | beta |
| cat_alpha_7y | Jensen's alpha % p.a. |
| cat_r_squared_7y | R-squared % |
| cat_correlation_7y | correlation |
| cat_tracking_error_7y | tracking error % p.a. |
| cat_active_return_7y | same as excess_return |
| cat_information_ratio_7y | information ratio |
| cat_treynor_7y | Treynor ratio % |
| cat_m2_7y | Modigliani M-squared % |
| cat_up_capture_7y | up-market capture % (geometric) |
| cat_down_capture_7y | down-market capture % (geometric) |
| cat_capture_ratio_7y | up capture / down capture |
| cat_up_capture_arith_7y | up-market capture % (geometric) |
| cat_down_capture_arith_7y | down-market capture % (geometric) |
| cat_batting_avg_7y | % of periods beating the benchmark |
| cat_up_batting_avg_7y |  |
| cat_down_batting_avg_7y |  |
| cat_bm_ann_return_7y | benchmark value of the same measure |
| cat_bm_std_dev_7y | benchmark value of the same measure |
| cat_excess_return_7y | annualised return minus benchmark's |
| obs_10y |  |
| ann_return_10y | annualised return % |
| std_dev_10y | annualised standard deviation % |
| downside_dev_10y | annualised downside deviation % (below risk-free) |
| sharpe_10y | Sharpe ratio |
| sortino_10y | Sortino ratio |
| skewness_10y | skewness |
| kurtosis_10y | excess kurtosis |
| var_95_10y | 95% value-at-risk per period % |
| cvar_95_10y | 95% expected shortfall per period % |
| omega_10y | Omega ratio |
| pct_positive_periods_10y |  |
| best_period_10y |  |
| worst_period_10y |  |
| mean_excess_per_period_10y |  |
| max_drawdown_10y | max drawdown % (daily) |
| dd_days_to_recover_10y |  |
| longest_underwater_days_10y | longest period below a previous peak (days) |
| ulcer_index_10y | Ulcer index |
| current_drawdown_10y | drawdown from peak at window end % |
| calmar_10y | annualised return / max drawdown |
| cat_obs_rel_10y |  |
| cat_beta_10y | beta |
| cat_alpha_10y | Jensen's alpha % p.a. |
| cat_r_squared_10y | R-squared % |
| cat_correlation_10y | correlation |
| cat_tracking_error_10y | tracking error % p.a. |
| cat_active_return_10y | same as excess_return |
| cat_information_ratio_10y | information ratio |
| cat_treynor_10y | Treynor ratio % |
| cat_m2_10y | Modigliani M-squared % |
| cat_up_capture_10y | up-market capture % (geometric) |
| cat_down_capture_10y | down-market capture % (geometric) |
| cat_capture_ratio_10y | up capture / down capture |
| cat_up_capture_arith_10y | up-market capture % (geometric) |
| cat_down_capture_arith_10y | down-market capture % (geometric) |
| cat_batting_avg_10y | % of periods beating the benchmark |
| cat_up_batting_avg_10y |  |
| cat_down_batting_avg_10y |  |
| cat_bm_ann_return_10y | benchmark value of the same measure |
| cat_bm_std_dev_10y | benchmark value of the same measure |
| cat_excess_return_10y | annualised return minus benchmark's |
| roll_obs_1y | rolling-return statistics over the last 10 years |
| roll_avg_1y | rolling-return statistics over the last 10 years |
| roll_median_1y | rolling-return statistics over the last 10 years |
| roll_min_1y | rolling-return statistics over the last 10 years |
| roll_max_1y | rolling-return statistics over the last 10 years |
| roll_std_1y | rolling-return statistics over the last 10 years |
| roll_pct_positive_1y | rolling-return statistics over the last 10 years |
| roll_pct_above_6_1y | rolling-return statistics over the last 10 years |
| roll_pct_above_10_1y | rolling-return statistics over the last 10 years |
| roll_pct_above_12_1y | rolling-return statistics over the last 10 years |
| roll_pct_above_15_1y | rolling-return statistics over the last 10 years |
| roll_obs_3y | rolling-return statistics over the last 10 years |
| roll_avg_3y | rolling-return statistics over the last 10 years |
| roll_median_3y | rolling-return statistics over the last 10 years |
| roll_min_3y | rolling-return statistics over the last 10 years |
| roll_max_3y | rolling-return statistics over the last 10 years |
| roll_std_3y | rolling-return statistics over the last 10 years |
| roll_pct_positive_3y | rolling-return statistics over the last 10 years |
| roll_pct_above_6_3y | rolling-return statistics over the last 10 years |
| roll_pct_above_10_3y | rolling-return statistics over the last 10 years |
| roll_pct_above_12_3y | rolling-return statistics over the last 10 years |
| roll_pct_above_15_3y | rolling-return statistics over the last 10 years |
| roll_obs_5y | rolling-return statistics over the last 10 years |
| roll_avg_5y | rolling-return statistics over the last 10 years |
| roll_median_5y | rolling-return statistics over the last 10 years |
| roll_min_5y | rolling-return statistics over the last 10 years |
| roll_max_5y | rolling-return statistics over the last 10 years |
| roll_std_5y | rolling-return statistics over the last 10 years |
| roll_pct_positive_5y | rolling-return statistics over the last 10 years |
| roll_pct_above_6_5y | rolling-return statistics over the last 10 years |
| roll_pct_above_10_5y | rolling-return statistics over the last 10 years |
| roll_pct_above_12_5y | rolling-return statistics over the last 10 years |
| roll_pct_above_15_5y | rolling-return statistics over the last 10 years |
| obs_rel_1y |  |
| beta_1y | beta |
| alpha_1y | Jensen's alpha % p.a. |
| r_squared_1y | R-squared % |
| correlation_1y | correlation |
| tracking_error_1y | tracking error % p.a. |
| active_return_1y | same as excess_return |
| information_ratio_1y | information ratio |
| treynor_1y | Treynor ratio % |
| m2_1y | Modigliani M-squared % |
| up_capture_1y | up-market capture % (geometric) |
| down_capture_1y | down-market capture % (geometric) |
| capture_ratio_1y | up capture / down capture |
| up_capture_arith_1y | up-market capture % (geometric) |
| down_capture_arith_1y | down-market capture % (geometric) |
| batting_avg_1y | % of periods beating the benchmark |
| up_batting_avg_1y |  |
| down_batting_avg_1y |  |
| bm_ann_return_1y | benchmark value of the same measure |
| bm_std_dev_1y | benchmark value of the same measure |
| excess_return_1y | annualised return minus benchmark's |
| obs_rel_3y |  |
| beta_3y | beta |
| alpha_3y | Jensen's alpha % p.a. |
| r_squared_3y | R-squared % |
| correlation_3y | correlation |
| tracking_error_3y | tracking error % p.a. |
| active_return_3y | same as excess_return |
| information_ratio_3y | information ratio |
| treynor_3y | Treynor ratio % |
| m2_3y | Modigliani M-squared % |
| up_capture_3y | up-market capture % (geometric) |
| down_capture_3y | down-market capture % (geometric) |
| capture_ratio_3y | up capture / down capture |
| up_capture_arith_3y | up-market capture % (geometric) |
| down_capture_arith_3y | down-market capture % (geometric) |
| batting_avg_3y | % of periods beating the benchmark |
| up_batting_avg_3y |  |
| down_batting_avg_3y |  |
| bm_ann_return_3y | benchmark value of the same measure |
| bm_std_dev_3y | benchmark value of the same measure |
| excess_return_3y | annualised return minus benchmark's |
| obs_rel_5y |  |
| beta_5y | beta |
| alpha_5y | Jensen's alpha % p.a. |
| r_squared_5y | R-squared % |
| correlation_5y | correlation |
| tracking_error_5y | tracking error % p.a. |
| active_return_5y | same as excess_return |
| information_ratio_5y | information ratio |
| treynor_5y | Treynor ratio % |
| m2_5y | Modigliani M-squared % |
| up_capture_5y | up-market capture % (geometric) |
| down_capture_5y | down-market capture % (geometric) |
| capture_ratio_5y | up capture / down capture |
| up_capture_arith_5y | up-market capture % (geometric) |
| down_capture_arith_5y | down-market capture % (geometric) |
| batting_avg_5y | % of periods beating the benchmark |
| up_batting_avg_5y |  |
| down_batting_avg_5y |  |
| bm_ann_return_5y | benchmark value of the same measure |
| bm_std_dev_5y | benchmark value of the same measure |
| excess_return_5y | annualised return minus benchmark's |
| roll_bm_avg_1y | rolling-return statistics over the last 10 years |
| roll_pct_beat_bm_1y | rolling-return statistics over the last 10 years |
| roll_avg_outperformance_1y | rolling-return statistics over the last 10 years |
| roll_bm_avg_3y | rolling-return statistics over the last 10 years |
| roll_pct_beat_bm_3y | rolling-return statistics over the last 10 years |
| roll_avg_outperformance_3y | rolling-return statistics over the last 10 years |
| roll_bm_avg_5y | rolling-return statistics over the last 10 years |
| roll_pct_beat_bm_5y | rolling-return statistics over the last 10 years |
| roll_avg_outperformance_5y | rolling-return statistics over the last 10 years |
| obs_rel_7y |  |
| beta_7y | beta |
| alpha_7y | Jensen's alpha % p.a. |
| r_squared_7y | R-squared % |
| correlation_7y | correlation |
| tracking_error_7y | tracking error % p.a. |
| active_return_7y | same as excess_return |
| information_ratio_7y | information ratio |
| treynor_7y | Treynor ratio % |
| m2_7y | Modigliani M-squared % |
| up_capture_7y | up-market capture % (geometric) |
| down_capture_7y | down-market capture % (geometric) |
| capture_ratio_7y | up capture / down capture |
| up_capture_arith_7y | up-market capture % (geometric) |
| down_capture_arith_7y | down-market capture % (geometric) |
| batting_avg_7y | % of periods beating the benchmark |
| up_batting_avg_7y |  |
| down_batting_avg_7y |  |
| bm_ann_return_7y | benchmark value of the same measure |
| bm_std_dev_7y | benchmark value of the same measure |
| excess_return_7y | annualised return minus benchmark's |
| obs_rel_10y |  |
| beta_10y | beta |
| alpha_10y | Jensen's alpha % p.a. |
| r_squared_10y | R-squared % |
| correlation_10y | correlation |
| tracking_error_10y | tracking error % p.a. |
| active_return_10y | same as excess_return |
| information_ratio_10y | information ratio |
| treynor_10y | Treynor ratio % |
| m2_10y | Modigliani M-squared % |
| up_capture_10y | up-market capture % (geometric) |
| down_capture_10y | down-market capture % (geometric) |
| capture_ratio_10y | up capture / down capture |
| up_capture_arith_10y | up-market capture % (geometric) |
| down_capture_arith_10y | down-market capture % (geometric) |
| batting_avg_10y | % of periods beating the benchmark |
| up_batting_avg_10y |  |
| down_batting_avg_10y |  |
| bm_ann_return_10y | benchmark value of the same measure |
| bm_std_dev_10y | benchmark value of the same measure |
| excess_return_10y | annualised return minus benchmark's |
| metrics_basis |  |
| bm_ret_1m | benchmark value of the same measure |
| bm_ret_3m | benchmark value of the same measure |
| bm_ret_6m | benchmark value of the same measure |
| bm_ret_ytd | benchmark value of the same measure |
| bm_ret_1y | benchmark value of the same measure |
| bm_ret_2y | benchmark value of the same measure |
| bm_ret_3y | benchmark value of the same measure |
| bm_ret_5y | benchmark value of the same measure |
| bm_ret_7y | benchmark value of the same measure |
| bm_ret_10y | benchmark value of the same measure |
| bm_ret_si | benchmark value of the same measure |
| catidx_ret_1m | category-average index trailing return |
| catidx_ret_3m | category-average index trailing return |
| catidx_ret_6m | category-average index trailing return |
| catidx_ret_ytd | category-average index trailing return |
| catidx_ret_1y | category-average index trailing return |
| catidx_ret_2y | category-average index trailing return |
| catidx_ret_3y | category-average index trailing return |
| catidx_ret_5y | category-average index trailing return |
| catidx_ret_7y | category-average index trailing return |
| catidx_ret_10y | category-average index trailing return |
| catidx_ret_si | category-average index trailing return |
| ret_1m_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_1m_of | trailing point-to-point return %, CAGR above 1 year |
| ret_1m_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_1m_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_3m_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_3m_of | trailing point-to-point return %, CAGR above 1 year |
| ret_3m_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_3m_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_6m_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_6m_of | trailing point-to-point return %, CAGR above 1 year |
| ret_6m_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_6m_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_ytd_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_ytd_of | trailing point-to-point return %, CAGR above 1 year |
| ret_ytd_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_ytd_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_1y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_1y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_1y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_1y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_2y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_2y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_2y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_2y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_3y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_3y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_3y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_3y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_5y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_5y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_5y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_5y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_7y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_7y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_7y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_7y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ret_10y_rank | trailing point-to-point return %, CAGR above 1 year |
| ret_10y_of | trailing point-to-point return %, CAGR above 1 year |
| ret_10y_pctile | trailing point-to-point return %, CAGR above 1 year |
| ret_10y_quartile | trailing point-to-point return %, CAGR above 1 year |
| ann_return_1y_rank | annualised return % |
| ann_return_1y_of | annualised return % |
| ann_return_1y_pctile | annualised return % |
| ann_return_1y_quartile | annualised return % |
| std_dev_1y_rank | annualised standard deviation % |
| std_dev_1y_of | annualised standard deviation % |
| std_dev_1y_pctile | annualised standard deviation % |
| std_dev_1y_quartile | annualised standard deviation % |
| downside_dev_1y_rank | annualised downside deviation % (below risk-free) |
| downside_dev_1y_of | annualised downside deviation % (below risk-free) |
| downside_dev_1y_pctile | annualised downside deviation % (below risk-free) |
| downside_dev_1y_quartile | annualised downside deviation % (below risk-free) |
| sharpe_1y_rank | Sharpe ratio |
| sharpe_1y_of | Sharpe ratio |
| sharpe_1y_pctile | Sharpe ratio |
| sharpe_1y_quartile | Sharpe ratio |
| sortino_1y_rank | Sortino ratio |
| sortino_1y_of | Sortino ratio |
| sortino_1y_pctile | Sortino ratio |
| sortino_1y_quartile | Sortino ratio |
| calmar_1y_rank | annualised return / max drawdown |
| calmar_1y_of | annualised return / max drawdown |
| calmar_1y_pctile | annualised return / max drawdown |
| calmar_1y_quartile | annualised return / max drawdown |
| max_drawdown_1y_rank | max drawdown % (daily) |
| max_drawdown_1y_of | max drawdown % (daily) |
| max_drawdown_1y_pctile | max drawdown % (daily) |
| max_drawdown_1y_quartile | max drawdown % (daily) |
| alpha_1y_rank | Jensen's alpha % p.a. |
| alpha_1y_of | Jensen's alpha % p.a. |
| alpha_1y_pctile | Jensen's alpha % p.a. |
| alpha_1y_quartile | Jensen's alpha % p.a. |
| information_ratio_1y_rank | information ratio |
| information_ratio_1y_of | information ratio |
| information_ratio_1y_pctile | information ratio |
| information_ratio_1y_quartile | information ratio |
| capture_ratio_1y_rank | up capture / down capture |
| capture_ratio_1y_of | up capture / down capture |
| capture_ratio_1y_pctile | up capture / down capture |
| capture_ratio_1y_quartile | up capture / down capture |
| up_capture_1y_rank | up-market capture % (geometric) |
| up_capture_1y_of | up-market capture % (geometric) |
| up_capture_1y_pctile | up-market capture % (geometric) |
| up_capture_1y_quartile | up-market capture % (geometric) |
| down_capture_1y_rank | down-market capture % (geometric) |
| down_capture_1y_of | down-market capture % (geometric) |
| down_capture_1y_pctile | down-market capture % (geometric) |
| down_capture_1y_quartile | down-market capture % (geometric) |
| batting_avg_1y_rank | % of periods beating the benchmark |
| batting_avg_1y_of | % of periods beating the benchmark |
| batting_avg_1y_pctile | % of periods beating the benchmark |
| batting_avg_1y_quartile | % of periods beating the benchmark |
| excess_return_1y_rank | annualised return minus benchmark's |
| excess_return_1y_of | annualised return minus benchmark's |
| excess_return_1y_pctile | annualised return minus benchmark's |
| excess_return_1y_quartile | annualised return minus benchmark's |
| ann_return_3y_rank | annualised return % |
| ann_return_3y_of | annualised return % |
| ann_return_3y_pctile | annualised return % |
| ann_return_3y_quartile | annualised return % |
| std_dev_3y_rank | annualised standard deviation % |
| std_dev_3y_of | annualised standard deviation % |
| std_dev_3y_pctile | annualised standard deviation % |
| std_dev_3y_quartile | annualised standard deviation % |
| downside_dev_3y_rank | annualised downside deviation % (below risk-free) |
| downside_dev_3y_of | annualised downside deviation % (below risk-free) |
| downside_dev_3y_pctile | annualised downside deviation % (below risk-free) |
| downside_dev_3y_quartile | annualised downside deviation % (below risk-free) |
| sharpe_3y_rank | Sharpe ratio |
| sharpe_3y_of | Sharpe ratio |
| sharpe_3y_pctile | Sharpe ratio |
| sharpe_3y_quartile | Sharpe ratio |
| sortino_3y_rank | Sortino ratio |
| sortino_3y_of | Sortino ratio |
| sortino_3y_pctile | Sortino ratio |
| sortino_3y_quartile | Sortino ratio |
| calmar_3y_rank | annualised return / max drawdown |
| calmar_3y_of | annualised return / max drawdown |
| calmar_3y_pctile | annualised return / max drawdown |
| calmar_3y_quartile | annualised return / max drawdown |
| max_drawdown_3y_rank | max drawdown % (daily) |
| max_drawdown_3y_of | max drawdown % (daily) |
| max_drawdown_3y_pctile | max drawdown % (daily) |
| max_drawdown_3y_quartile | max drawdown % (daily) |
| alpha_3y_rank | Jensen's alpha % p.a. |
| alpha_3y_of | Jensen's alpha % p.a. |
| alpha_3y_pctile | Jensen's alpha % p.a. |
| alpha_3y_quartile | Jensen's alpha % p.a. |
| information_ratio_3y_rank | information ratio |
| information_ratio_3y_of | information ratio |
| information_ratio_3y_pctile | information ratio |
| information_ratio_3y_quartile | information ratio |
| capture_ratio_3y_rank | up capture / down capture |
| capture_ratio_3y_of | up capture / down capture |
| capture_ratio_3y_pctile | up capture / down capture |
| capture_ratio_3y_quartile | up capture / down capture |
| up_capture_3y_rank | up-market capture % (geometric) |
| up_capture_3y_of | up-market capture % (geometric) |
| up_capture_3y_pctile | up-market capture % (geometric) |
| up_capture_3y_quartile | up-market capture % (geometric) |
| down_capture_3y_rank | down-market capture % (geometric) |
| down_capture_3y_of | down-market capture % (geometric) |
| down_capture_3y_pctile | down-market capture % (geometric) |
| down_capture_3y_quartile | down-market capture % (geometric) |
| batting_avg_3y_rank | % of periods beating the benchmark |
| batting_avg_3y_of | % of periods beating the benchmark |
| batting_avg_3y_pctile | % of periods beating the benchmark |
| batting_avg_3y_quartile | % of periods beating the benchmark |
| excess_return_3y_rank | annualised return minus benchmark's |
| excess_return_3y_of | annualised return minus benchmark's |
| excess_return_3y_pctile | annualised return minus benchmark's |
| excess_return_3y_quartile | annualised return minus benchmark's |
| ann_return_5y_rank | annualised return % |
| ann_return_5y_of | annualised return % |
| ann_return_5y_pctile | annualised return % |
| ann_return_5y_quartile | annualised return % |
| std_dev_5y_rank | annualised standard deviation % |
| std_dev_5y_of | annualised standard deviation % |
| std_dev_5y_pctile | annualised standard deviation % |
| std_dev_5y_quartile | annualised standard deviation % |
| downside_dev_5y_rank | annualised downside deviation % (below risk-free) |
| downside_dev_5y_of | annualised downside deviation % (below risk-free) |
| downside_dev_5y_pctile | annualised downside deviation % (below risk-free) |
| downside_dev_5y_quartile | annualised downside deviation % (below risk-free) |
| sharpe_5y_rank | Sharpe ratio |
| sharpe_5y_of | Sharpe ratio |
| sharpe_5y_pctile | Sharpe ratio |
| sharpe_5y_quartile | Sharpe ratio |
| sortino_5y_rank | Sortino ratio |
| sortino_5y_of | Sortino ratio |
| sortino_5y_pctile | Sortino ratio |
| sortino_5y_quartile | Sortino ratio |
| calmar_5y_rank | annualised return / max drawdown |
| calmar_5y_of | annualised return / max drawdown |
| calmar_5y_pctile | annualised return / max drawdown |
| calmar_5y_quartile | annualised return / max drawdown |
| max_drawdown_5y_rank | max drawdown % (daily) |
| max_drawdown_5y_of | max drawdown % (daily) |
| max_drawdown_5y_pctile | max drawdown % (daily) |
| max_drawdown_5y_quartile | max drawdown % (daily) |
| alpha_5y_rank | Jensen's alpha % p.a. |
| alpha_5y_of | Jensen's alpha % p.a. |
| alpha_5y_pctile | Jensen's alpha % p.a. |
| alpha_5y_quartile | Jensen's alpha % p.a. |
| information_ratio_5y_rank | information ratio |
| information_ratio_5y_of | information ratio |
| information_ratio_5y_pctile | information ratio |
| information_ratio_5y_quartile | information ratio |
| capture_ratio_5y_rank | up capture / down capture |
| capture_ratio_5y_of | up capture / down capture |
| capture_ratio_5y_pctile | up capture / down capture |
| capture_ratio_5y_quartile | up capture / down capture |
| up_capture_5y_rank | up-market capture % (geometric) |
| up_capture_5y_of | up-market capture % (geometric) |
| up_capture_5y_pctile | up-market capture % (geometric) |
| up_capture_5y_quartile | up-market capture % (geometric) |
| down_capture_5y_rank | down-market capture % (geometric) |
| down_capture_5y_of | down-market capture % (geometric) |
| down_capture_5y_pctile | down-market capture % (geometric) |
| down_capture_5y_quartile | down-market capture % (geometric) |
| batting_avg_5y_rank | % of periods beating the benchmark |
| batting_avg_5y_of | % of periods beating the benchmark |
| batting_avg_5y_pctile | % of periods beating the benchmark |
| batting_avg_5y_quartile | % of periods beating the benchmark |
| excess_return_5y_rank | annualised return minus benchmark's |
| excess_return_5y_of | annualised return minus benchmark's |
| excess_return_5y_pctile | annualised return minus benchmark's |
| excess_return_5y_quartile | annualised return minus benchmark's |
| ann_return_7y_rank | annualised return % |
| ann_return_7y_of | annualised return % |
| ann_return_7y_pctile | annualised return % |
| ann_return_7y_quartile | annualised return % |
| std_dev_7y_rank | annualised standard deviation % |
| std_dev_7y_of | annualised standard deviation % |
| std_dev_7y_pctile | annualised standard deviation % |
| std_dev_7y_quartile | annualised standard deviation % |
| downside_dev_7y_rank | annualised downside deviation % (below risk-free) |
| downside_dev_7y_of | annualised downside deviation % (below risk-free) |
| downside_dev_7y_pctile | annualised downside deviation % (below risk-free) |
| downside_dev_7y_quartile | annualised downside deviation % (below risk-free) |
| sharpe_7y_rank | Sharpe ratio |
| sharpe_7y_of | Sharpe ratio |
| sharpe_7y_pctile | Sharpe ratio |
| sharpe_7y_quartile | Sharpe ratio |
| sortino_7y_rank | Sortino ratio |
| sortino_7y_of | Sortino ratio |
| sortino_7y_pctile | Sortino ratio |
| sortino_7y_quartile | Sortino ratio |
| calmar_7y_rank | annualised return / max drawdown |
| calmar_7y_of | annualised return / max drawdown |
| calmar_7y_pctile | annualised return / max drawdown |
| calmar_7y_quartile | annualised return / max drawdown |
| max_drawdown_7y_rank | max drawdown % (daily) |
| max_drawdown_7y_of | max drawdown % (daily) |
| max_drawdown_7y_pctile | max drawdown % (daily) |
| max_drawdown_7y_quartile | max drawdown % (daily) |
| alpha_7y_rank | Jensen's alpha % p.a. |
| alpha_7y_of | Jensen's alpha % p.a. |
| alpha_7y_pctile | Jensen's alpha % p.a. |
| alpha_7y_quartile | Jensen's alpha % p.a. |
| information_ratio_7y_rank | information ratio |
| information_ratio_7y_of | information ratio |
| information_ratio_7y_pctile | information ratio |
| information_ratio_7y_quartile | information ratio |
| capture_ratio_7y_rank | up capture / down capture |
| capture_ratio_7y_of | up capture / down capture |
| capture_ratio_7y_pctile | up capture / down capture |
| capture_ratio_7y_quartile | up capture / down capture |
| up_capture_7y_rank | up-market capture % (geometric) |
| up_capture_7y_of | up-market capture % (geometric) |
| up_capture_7y_pctile | up-market capture % (geometric) |
| up_capture_7y_quartile | up-market capture % (geometric) |
| down_capture_7y_rank | down-market capture % (geometric) |
| down_capture_7y_of | down-market capture % (geometric) |
| down_capture_7y_pctile | down-market capture % (geometric) |
| down_capture_7y_quartile | down-market capture % (geometric) |
| batting_avg_7y_rank | % of periods beating the benchmark |
| batting_avg_7y_of | % of periods beating the benchmark |
| batting_avg_7y_pctile | % of periods beating the benchmark |
| batting_avg_7y_quartile | % of periods beating the benchmark |
| excess_return_7y_rank | annualised return minus benchmark's |
| excess_return_7y_of | annualised return minus benchmark's |
| excess_return_7y_pctile | annualised return minus benchmark's |
| excess_return_7y_quartile | annualised return minus benchmark's |
| ann_return_10y_rank | annualised return % |
| ann_return_10y_of | annualised return % |
| ann_return_10y_pctile | annualised return % |
| ann_return_10y_quartile | annualised return % |
| std_dev_10y_rank | annualised standard deviation % |
| std_dev_10y_of | annualised standard deviation % |
| std_dev_10y_pctile | annualised standard deviation % |
| std_dev_10y_quartile | annualised standard deviation % |
| downside_dev_10y_rank | annualised downside deviation % (below risk-free) |
| downside_dev_10y_of | annualised downside deviation % (below risk-free) |
| downside_dev_10y_pctile | annualised downside deviation % (below risk-free) |
| downside_dev_10y_quartile | annualised downside deviation % (below risk-free) |
| sharpe_10y_rank | Sharpe ratio |
| sharpe_10y_of | Sharpe ratio |
| sharpe_10y_pctile | Sharpe ratio |
| sharpe_10y_quartile | Sharpe ratio |
| sortino_10y_rank | Sortino ratio |
| sortino_10y_of | Sortino ratio |
| sortino_10y_pctile | Sortino ratio |
| sortino_10y_quartile | Sortino ratio |
| calmar_10y_rank | annualised return / max drawdown |
| calmar_10y_of | annualised return / max drawdown |
| calmar_10y_pctile | annualised return / max drawdown |
| calmar_10y_quartile | annualised return / max drawdown |
| max_drawdown_10y_rank | max drawdown % (daily) |
| max_drawdown_10y_of | max drawdown % (daily) |
| max_drawdown_10y_pctile | max drawdown % (daily) |
| max_drawdown_10y_quartile | max drawdown % (daily) |
| alpha_10y_rank | Jensen's alpha % p.a. |
| alpha_10y_of | Jensen's alpha % p.a. |
| alpha_10y_pctile | Jensen's alpha % p.a. |
| alpha_10y_quartile | Jensen's alpha % p.a. |
| information_ratio_10y_rank | information ratio |
| information_ratio_10y_of | information ratio |
| information_ratio_10y_pctile | information ratio |
| information_ratio_10y_quartile | information ratio |
| capture_ratio_10y_rank | up capture / down capture |
| capture_ratio_10y_of | up capture / down capture |
| capture_ratio_10y_pctile | up capture / down capture |
| capture_ratio_10y_quartile | up capture / down capture |
| up_capture_10y_rank | up-market capture % (geometric) |
| up_capture_10y_of | up-market capture % (geometric) |
| up_capture_10y_pctile | up-market capture % (geometric) |
| up_capture_10y_quartile | up-market capture % (geometric) |
| down_capture_10y_rank | down-market capture % (geometric) |
| down_capture_10y_of | down-market capture % (geometric) |
| down_capture_10y_pctile | down-market capture % (geometric) |
| down_capture_10y_quartile | down-market capture % (geometric) |
| batting_avg_10y_rank | % of periods beating the benchmark |
| batting_avg_10y_of | % of periods beating the benchmark |
| batting_avg_10y_pctile | % of periods beating the benchmark |
| batting_avg_10y_quartile | % of periods beating the benchmark |
| excess_return_10y_rank | annualised return minus benchmark's |
| excess_return_10y_of | annualised return minus benchmark's |
| excess_return_10y_pctile | annualised return minus benchmark's |
| excess_return_10y_quartile | annualised return minus benchmark's |
| roll_avg_1y_rank | rolling-return statistics over the last 10 years |
| roll_avg_1y_of | rolling-return statistics over the last 10 years |
| roll_avg_1y_pctile | rolling-return statistics over the last 10 years |
| roll_avg_1y_quartile | rolling-return statistics over the last 10 years |
| roll_avg_3y_rank | rolling-return statistics over the last 10 years |
| roll_avg_3y_of | rolling-return statistics over the last 10 years |
| roll_avg_3y_pctile | rolling-return statistics over the last 10 years |
| roll_avg_3y_quartile | rolling-return statistics over the last 10 years |
| roll_avg_5y_rank | rolling-return statistics over the last 10 years |
| roll_avg_5y_of | rolling-return statistics over the last 10 years |
| roll_avg_5y_pctile | rolling-return statistics over the last 10 years |
| roll_avg_5y_quartile | rolling-return statistics over the last 10 years |
| peers |  |
| cat_avg_ret_1m | simple average of peers |
| cat_avg_ret_3m | simple average of peers |
| cat_avg_ret_6m | simple average of peers |
| cat_avg_ret_ytd | simple average of peers |
| cat_avg_ret_1y | simple average of peers |
| cat_avg_ret_2y | simple average of peers |
| cat_avg_ret_3y | simple average of peers |
| cat_avg_ret_5y | simple average of peers |
| cat_avg_ret_7y | simple average of peers |
| cat_avg_ret_10y | simple average of peers |
| cat_avg_ann_return_1y | simple average of peers |
| cat_avg_std_dev_1y | simple average of peers |
| cat_avg_downside_dev_1y | simple average of peers |
| cat_avg_sharpe_1y | simple average of peers |
| cat_avg_sortino_1y | simple average of peers |
| cat_avg_calmar_1y | simple average of peers |
| cat_avg_max_drawdown_1y | simple average of peers |
| cat_avg_alpha_1y | simple average of peers |
| cat_avg_information_ratio_1y | simple average of peers |
| cat_avg_capture_ratio_1y | simple average of peers |
| cat_avg_up_capture_1y | simple average of peers |
| cat_avg_down_capture_1y | simple average of peers |
| cat_avg_batting_avg_1y | simple average of peers |
| cat_avg_excess_return_1y | simple average of peers |
| cat_avg_ann_return_3y | simple average of peers |
| cat_avg_std_dev_3y | simple average of peers |
| cat_avg_downside_dev_3y | simple average of peers |
| cat_avg_sharpe_3y | simple average of peers |
| cat_avg_sortino_3y | simple average of peers |
| cat_avg_calmar_3y | simple average of peers |
| cat_avg_max_drawdown_3y | simple average of peers |
| cat_avg_alpha_3y | simple average of peers |
| cat_avg_information_ratio_3y | simple average of peers |
| cat_avg_capture_ratio_3y | simple average of peers |
| cat_avg_up_capture_3y | simple average of peers |
| cat_avg_down_capture_3y | simple average of peers |
| cat_avg_batting_avg_3y | simple average of peers |
| cat_avg_excess_return_3y | simple average of peers |
| cat_avg_ann_return_5y | simple average of peers |
| cat_avg_std_dev_5y | simple average of peers |
| cat_avg_downside_dev_5y | simple average of peers |
| cat_avg_sharpe_5y | simple average of peers |
| cat_avg_sortino_5y | simple average of peers |
| cat_avg_calmar_5y | simple average of peers |
| cat_avg_max_drawdown_5y | simple average of peers |
| cat_avg_alpha_5y | simple average of peers |
| cat_avg_information_ratio_5y | simple average of peers |
| cat_avg_capture_ratio_5y | simple average of peers |
| cat_avg_up_capture_5y | simple average of peers |
| cat_avg_down_capture_5y | simple average of peers |
| cat_avg_batting_avg_5y | simple average of peers |
| cat_avg_excess_return_5y | simple average of peers |
| cat_avg_ann_return_7y | simple average of peers |
| cat_avg_std_dev_7y | simple average of peers |
| cat_avg_downside_dev_7y | simple average of peers |
| cat_avg_sharpe_7y | simple average of peers |
| cat_avg_sortino_7y | simple average of peers |
| cat_avg_calmar_7y | simple average of peers |
| cat_avg_max_drawdown_7y | simple average of peers |
| cat_avg_alpha_7y | simple average of peers |
| cat_avg_information_ratio_7y | simple average of peers |
| cat_avg_capture_ratio_7y | simple average of peers |
| cat_avg_up_capture_7y | simple average of peers |
| cat_avg_down_capture_7y | simple average of peers |
| cat_avg_batting_avg_7y | simple average of peers |
| cat_avg_excess_return_7y | simple average of peers |
| cat_avg_ann_return_10y | simple average of peers |
| cat_avg_std_dev_10y | simple average of peers |
| cat_avg_downside_dev_10y | simple average of peers |
| cat_avg_sharpe_10y | simple average of peers |
| cat_avg_sortino_10y | simple average of peers |
| cat_avg_calmar_10y | simple average of peers |
| cat_avg_max_drawdown_10y | simple average of peers |
| cat_avg_alpha_10y | simple average of peers |
| cat_avg_information_ratio_10y | simple average of peers |
| cat_avg_capture_ratio_10y | simple average of peers |
| cat_avg_up_capture_10y | simple average of peers |
| cat_avg_down_capture_10y | simple average of peers |
| cat_avg_batting_avg_10y | simple average of peers |
| cat_avg_excess_return_10y | simple average of peers |
| cat_avg_roll_avg_1y | simple average of peers |
| cat_avg_roll_avg_3y | simple average of peers |
| cat_avg_roll_avg_5y | simple average of peers |
| risk_window_end |  |
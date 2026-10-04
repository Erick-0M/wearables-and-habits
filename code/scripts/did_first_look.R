# Exploratory Callaway-Sant'Anna event studies on the user-quarter panel (issue #5). Run in container from /home/repo-intro.
suppressMessages({library(did); library(ggplot2); library(data.table)})
O <- "analysis/outputs/"
d <- fread("build/interm/panel_user_quarter.csv")
outs <- c(med_d = "Medication purchase (any)", run_any_d = "Running-related purchase (any)", run_shoe_d = "Running-shoe purchase (any)",
          fit_gear_d = "Fitness-gear purchase (any)", supp_d = "Supplement purchase (any)")
res <- list()
for (gn in c("g", "g_clean")) for (y in names(outs)) {
  fit <- tryCatch(att_gt(yname = y, tname = "t", idname = "uidn", gname = gn, data = as.data.frame(d), xformla = ~1,
                         control_group = "notyettreated", allow_unbalanced_panel = TRUE, base_period = "universal", bstrap = TRUE, cband = FALSE),
                  error = function(e) {message(gn, y, ": ", e$message); NULL})
  if (is.null(fit)) next
  es <- aggte(fit, type = "dynamic", min_e = -8, max_e = 8, na.rm = TRUE)
  ov <- aggte(fit, type = "simple", na.rm = TRUE)
  res[[paste(gn, y)]] <- data.table(treat = ifelse(gn == "g", "Non-kids trackers", "Clean trackers"), outcome = outs[[y]], e = es$egt, att = es$att.egt, se = es$se.egt,
                                    overall = ov$overall.att, overall_se = ov$overall.se)
}
R <- rbindlist(res); fwrite(R, "analysis/outputs/did_first_look_results.csv")
R[, outcome := factor(outcome, levels = unname(outs))]
p <- ggplot(R, aes(e, att, color = treat)) + geom_hline(yintercept = 0, color = "grey50") + geom_vline(xintercept = -0.5, linetype = 2, color = "grey50") +
  geom_pointrange(aes(ymin = att - 1.96 * se, ymax = att + 1.96 * se), position = position_dodge(0.5), size = 0.25) +
  facet_wrap(~outcome, scales = "free_y", ncol = 2) + labs(x = "Quarters since first tracker purchase", y = "ATT on P(any purchase in quarter)", color = NULL) +
  theme_minimal(base_size = 10) + theme(legend.position = "bottom")
ggsave(paste0(O, "did_first_look_event_study.png"), p, width = 9, height = 9, dpi = 130)
print(unique(R[, .(treat, outcome, overall = round(overall, 4), overall_se = round(overall_se, 4))]))

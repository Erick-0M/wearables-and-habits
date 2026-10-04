# Balanced-panel robustness (issue #7). Exploratory.
# Run in research-container from /home/repo-intro:  Rscript scripts/design_did_balanced.R
# Balanced = users observed in every quarter 2018Q1-2022Q4 (first purchase <= 2018Q1, last >= 2022Q4); treated also need
# adoption in 2019Q1-2021Q4 so the event window -4..+4 is fully observed for every cohort. Reference period e=-1.
suppressMessages({library(did); library(dplyr)})
O <- "analysis/outputs/"; P <- read.csv("build/interm/design_panel_q.csv")
T0 <- 2018*4+1; T1 <- 2022*4+4
span <- P %>% group_by(id) %>% summarise(t0 = min(t), t1 = max(t))
bal_ids <- span$id[span$t0 <= T0 & span$t1 >= T1]
OUT <- c(run_shoe_d = "Running shoe", run_any_d = "Running-related (keyword)", fit_gear_d = "Fitness gear", supp_d = "Supplements",
         med_d = "Medication", pet_d = "PLACEBO: pet", book_d = "PLACEBO: books", giftcard_d = "PLACEBO: gift cards",
         cable_d = "PLACEBO: cables/batteries", cleaning_d = "PLACEBO: cleaning", grocery_d = "PLACEBO: grocery/food",
         ln_n = "General: ln(1+#purchases)", ln_spend = "General: ln(1+spend)")

est <- function(df, gname, y, balanced) {
  df$G <- ifelse(is.na(df[[gname]]), 0, df[[gname]])
  at <- att_gt(yname = y, tname = "t", idname = "id", gname = "G", data = df, control_group = "nevertreated", base_period = "universal",
               allow_unbalanced_panel = !balanced, bstrap = FALSE, cband = FALSE, est_method = "reg")
  es <- aggte(at, type = "dynamic", min_e = -4, max_e = 4, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
  po <- aggte(at, type = "dynamic", min_e = 1, max_e = 4, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
  list(es = data.frame(e = es$egt, att = es$att.egt, se = es$se.egt), post = c(po$overall.att, po$overall.se),
       nT = length(unique(df$id[df$G > 0])), nC = length(unique(df$id[df$G == 0])))
}
S <- list(); E <- list()
for (sp in list(list("main_all", "s_g", "g_q"), list("main_clean", "s_g_clean", "g_clean_q"))) {
  base <- P[P[[sp[[2]]]] == 1, ]
  gok <- is.na(base[[sp[[3]]]]) | (base[[sp[[3]]]] >= 2019*4+1 & base[[sp[[3]]]] <= 2021*4+4)
  cohort <- base[gok, ]                                  # same treated cohorts in both; unbalanced keeps all controls
  bal <- cohort[cohort$id %in% bal_ids & cohort$t >= T0 & cohort$t <= T1, ]
  for (y in names(OUT)) for (b in c(TRUE, FALSE)) {
    d <- if (b) bal else cohort
    r <- tryCatch(est(d, sp[[3]], y, b), error = function(e) { message("FAIL ", sp[[1]], y, b, conditionMessage(e)); NULL })
    if (is.null(r)) next
    k <- paste(sp[[1]], y, if (b) "balanced" else "unbalanced", sep = "|")
    S[[k]] <- data.frame(spec = sp[[1]], outcome = y, name = OUT[[y]], panel = if (b) "balanced" else "unbalanced", post_att = r$post[1], post_se = r$post[2], n_treated = r$nT, n_ctrl = r$nC)
    E[[k]] <- cbind(r$es, spec = sp[[1]], outcome = y, name = OUT[[y]], panel = if (b) "balanced" else "unbalanced")
    cat(k, sprintf("post=%.4f (%.4f) nT=%d nC=%d\n", r$post[1], r$post[2], r$nT, r$nC))
  }
}
write.csv(bind_rows(S), paste0(O, "design_did_balanced_summary.csv"), row.names = FALSE)
write.csv(bind_rows(E), paste0(O, "design_did_balanced_eventstudy.csv"), row.names = FALSE)

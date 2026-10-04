# Staggered DiD (Callaway-Sant'Anna), issue #7. Exploratory.
# Run in research-container from /home/repo-intro:  Rscript scripts/design_did.R
# Event studies use base_period="universal" => reference period is e=-1 (coefficient at -1 is 0 by construction).
suppressMessages({library(did); library(dplyr); library(ggplot2)})
O <- "analysis/outputs/"; P <- read.csv("build/interm/design_panel_q.csv")
MINE <- -8; MAXE <- 8

run <- function(df, gname, y, label) {
  df <- df[!is.na(df[[y]]), ]
  df$G <- ifelse(is.na(df[[gname]]), 0, df[[gname]])
  res <- tryCatch({
    at <- att_gt(yname = y, tname = "t", idname = "id", gname = "G", data = df, control_group = "nevertreated",
                 base_period = "universal", allow_unbalanced_panel = TRUE, bstrap = FALSE, cband = FALSE, est_method = "reg")
    es <- aggte(at, type = "dynamic", min_e = MINE, max_e = MAXE, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
    po <- aggte(at, type = "dynamic", min_e = 1, max_e = MAXE, na.rm = TRUE, bstrap = FALSE, cband = FALSE)
    list(es = data.frame(e = es$egt, att = es$att.egt, se = es$se.egt), post = c(po$overall.att, po$overall.se),
         pre_p = if (is.null(at$Wpval)) NA_real_ else at$Wpval, n_treated = length(unique(df$id[df$G > 0])), n_ctrl = length(unique(df$id[df$G == 0])))
  }, error = function(e) { message("FAIL ", label, ": ", conditionMessage(e)); NULL })
  if (is.null(res)) return(NULL)
  res$es$label <- label; res
}

# ---- specifications: (sample flag, treatment timing, outcome list, sample filter)
OUT <- c(run_shoe_d = "Running shoe", run_any_d = "Running-related (keyword)", fit_gear_d = "Fitness gear",
         supp_d = "Supplements", med_d = "Medication",
         pet_d = "PLACEBO: pet", book_d = "PLACEBO: books", giftcard_d = "PLACEBO: gift cards", cable_d = "PLACEBO: cables/batteries",
         cleaning_d = "PLACEBO: cleaning", grocery_d = "PLACEBO: grocery/food",
         ln_shoe_price = "PLACEBO: ln shoe price (cond.)", ln_n = "General: ln(1+#purchases)", ln_spend = "General: ln(1+spend)")
specs <- list(
  main_all   = list(df = P[P$s_g == 1, ], g = "g_q", out = OUT),
  main_clean = list(df = P[P$s_g_clean == 1, ], g = "g_clean_q", out = OUT))
# bundling split: outcomes exclude the bundled shoe purchase itself for adopters
for (v in c("g", "g_clean")) {
  d <- P[P$s_g == 1 & v == "g" | P$s_g_clean == 1 & v == "g_clean", ]
  gq <- paste0(v, "_q"); ex <- c(paste0("run_shoe_ex_", v, "_d"), paste0("run_any_ex_", v, "_d"))
  d$run_shoe_x <- d[[ex[1]]]; d$run_any_x <- d[[ex[2]]]
  o <- c(run_shoe_x = "Running shoe (ex-bundle)", run_any_x = "Running-related (ex-bundle)", fit_gear_d = "Fitness gear", supp_d = "Supplements")
  specs[[paste0("bundle_", v)]] <- list(df = d, g = gq, out = o, bundle = paste0("bundle_", v))
}
# shoe as treatment
OS <- c(wear_d = "Wearable purchase", run_noshoe_d = "Running-related, non-shoe", fit_gear_d = "Fitness gear", supp_d = "Supplements",
        run_shoe_d = "Running shoe (repeat)", med_d = "PLACEBO-ish: medication", pet_d = "PLACEBO: pet", book_d = "PLACEBO: books")
specs$shoe_all <- list(df = P[P$s_g_shoe == 1, ], g = "g_shoe_q", out = OS)
specs$shoe_noadopt <- list(df = P[P$s_g_shoe == 1 & P$adopter == 0, ], g = "g_shoe_q", out = OS)

rows <- list(); ES <- list()
for (sn in names(specs)) {
  sp <- specs[[sn]]
  groups <- if (!is.null(sp$bundle)) {
    # treated split by bundling; same never-treated controls
    list(bundlers = sp$df[is.na(sp$df[[sp$g]]) | sp$df[[sp$bundle]] == 1, ], nonbundlers = sp$df[is.na(sp$df[[sp$g]]) | sp$df[[sp$bundle]] == 0, ])
  } else list(all = sp$df)
  for (gn in names(groups)) for (y in names(sp$out)) {
    lab <- paste(sn, gn, y, sep = "|")
    r <- run(groups[[gn]], sp$g, y, lab); if (is.null(r)) next
    ES[[lab]] <- cbind(r$es, spec = sn, grp = gn, outcome = y, name = sp$out[[y]])
    rows[[lab]] <- data.frame(spec = sn, grp = gn, outcome = y, name = sp$out[[y]], post_att = r$post[1], post_se = r$post[2],
                              pre_p = r$pre_p, n_treated = r$n_treated, n_ctrl = r$n_ctrl)
    cat(lab, sprintf("post=%.4f (%.4f) pre_p=%.3f nT=%d\n", r$post[1], r$post[2], r$pre_p, r$n_treated))
  }
}
S <- bind_rows(rows); E <- bind_rows(ES)
write.csv(S, paste0(O, "design_did_summary.csv"), row.names = FALSE)
write.csv(E, paste0(O, "design_did_eventstudy.csv"), row.names = FALSE)

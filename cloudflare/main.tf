# Cloudflare WAF & rate limiting as code (plan-only in this demo; no zone applied).
# Real problem for a card marketplace: price-scraper bots hammering search endpoints.

terraform {
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 4.0" }
  }
}

variable "zone_id" {
  type    = string
  default = "REPLACE_ME"
}

# Rate-limit card search: generous for humans, hostile to scrapers.
resource "cloudflare_ruleset" "rate_limit_search" {
  zone_id = var.zone_id
  name    = "marketplace-rate-limits"
  kind    = "zone"
  phase   = "http_ratelimit"

  rules {
    description = "Throttle card search scraping"
    expression  = "(http.request.uri.path matches \"^/cards/search\")"
    action      = "block"
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = 120
      mitigation_timeout  = 600
    }
  }
}

# Managed WAF rules + bot-fight challenge on checkout-like paths.
resource "cloudflare_ruleset" "waf_custom" {
  zone_id = var.zone_id
  name    = "marketplace-waf-custom"
  kind    = "zone"
  phase   = "http_request_firewall_custom"

  rules {
    description = "Challenge likely bots on offer/purchase endpoints"
    expression  = "(http.request.uri.path matches \"^/(offers|checkout)\") and (cf.bot_management.score lt 30)"
    action      = "managed_challenge"
  }

  rules {
    description = "Block requests with no user agent"
    expression  = "(http.user_agent eq \"\")"
    action      = "block"
  }
}

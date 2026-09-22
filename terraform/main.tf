resource "digitalocean_app" "sarjy" {
  project_id = digitalocean_project.sarjy.id

  spec {
    name   = var.app_name
    region = var.region

    alert {
      rule = "DEPLOYMENT_FAILED"
    }

    service {
      name               = "backend"
      instance_count     = 1
      instance_size_slug = "apps-d-1vcpu-2gb"
      source_dir         = "backend"
      dockerfile_path    = "backend/Dockerfile"
      http_port          = 8000

      github {
        repo           = var.github_repo
        branch         = var.branch
        deploy_on_push = var.deploy_on_push
      }

      env {
        key   = "OPENAI_API_KEY"
        value = var.openai_api_key
        type  = "SECRET"
        scope = "RUN_TIME"
      }

      env {
        key   = "OPENAI_MODEL"
        value = var.openai_model
      }

      env {
        key   = "DATABASE_URL"
        value = "sqlite:///./data/sarjy_memory.db"
      }

      env {
        key   = "STT_ENABLED"
        value = var.stt_enabled ? "true" : "false"
      }

      env {
        key   = "TTS_ENABLED"
        value = var.tts_enabled ? "true" : "false"
      }

      env {
        key   = "TTS_PROVIDER"
        value = var.tts_provider
      }

      env {
        key   = "WHISPER_MODEL"
        value = var.whisper_model
      }

      env {
        key   = "VAD_AGGRESSIVENESS"
        value = tostring(var.vad_aggressiveness)
      }

      env {
        key   = "VAD_MIN_SPEECH_MS"
        value = tostring(var.vad_min_speech_ms)
      }

      env {
        key   = "VAD_SILENCE_MS"
        value = tostring(var.vad_silence_ms)
      }

      env {
        key   = "VAD_BARGE_IN_MIN_SPEECH_MS"
        value = tostring(var.vad_barge_in_min_speech_ms)
      }

      env {
        key   = "MAX_UTTERANCE_MS"
        value = tostring(var.max_utterance_ms)
      }

      env {
        key   = "WHISPER_NO_SPEECH_THRESHOLD"
        value = tostring(var.whisper_no_speech_threshold)
      }

      env {
        key   = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        key   = "LOG_FORMAT"
        value = var.log_format
      }

      # Models load during startup, so allow a generous warm-up window.
      health_check {
        http_path             = "/"
        initial_delay_seconds = 120
        period_seconds        = 10
        timeout_seconds       = 5
        failure_threshold     = 30
        success_threshold     = 1
      }
    }

    static_site {
      name              = "frontend"
      source_dir        = "frontend"
      build_command     = "npm ci && npm run build"
      output_dir        = "dist"
      index_document    = "index.html"
      catchall_document = "index.html"

      # Baked into the bundle at build time so the SPA calls /api/* on the
      # same origin; ingress strips /api before forwarding to the backend.
      env {
        key   = "VITE_API_URL"
        value = "/api"
        scope = "BUILD_TIME"
      }

      github {
        repo           = var.github_repo
        branch         = var.branch
        deploy_on_push = var.deploy_on_push
      }
    }

    ingress {
      # All backend traffic is served under /api. The prefix is stripped before
      # forwarding, so the backend still receives /auth, /conversations, /ws, ...
      rule {
        component {
          name = "backend"
        }

        match {
          path {
            prefix = "/api"
          }
        }
      }

      # Everything else is served by the frontend static site.
      rule {
        component {
          name = "frontend"
        }

        match {
          path {
            prefix = "/"
          }
        }
      }
    }
  }
}

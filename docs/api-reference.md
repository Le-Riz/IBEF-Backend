# API Reference (Interactive)

This page displays the complete OpenAPI documentation for the IBEF Backend API.

<div id="swagger-ui"></div>

<link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@latest/swagger-ui.css" />
<script src="https://unpkg.com/swagger-ui-dist@latest/swagger-ui-bundle.js"></script>
<script src="https://unpkg.com/swagger-ui-dist@latest/swagger-ui-standalone-preset.js"></script>
<script>
  // Detect Material theme and sync with Swagger UI
  function getSwaggerTheme() {
    // Check if Material theme is in dark mode
    const isDark = document.body.getAttribute('data-md-color-scheme') === 'slate';
    return isDark ? 'dark' : 'light';
  }
  
  function applySwaggerTheme(theme) {
    const swaggerContainer = document.getElementById('swagger-ui');
    if (swaggerContainer) {
      swaggerContainer.setAttribute('data-theme', theme);
    }
  }
  
  // Load the OpenAPI spec and render Swagger UI
  window.onload = function() {
    const currentTheme = getSwaggerTheme();
    
    SwaggerUIBundle({
      url: '../assets/openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [
        SwaggerUIBundle.presets.apis,
        SwaggerUIStandalonePreset
      ],
      plugins: [
        SwaggerUIBundle.plugins.DownloadUrl
      ],
      layout: "StandaloneLayout",
      defaultModelsExpandDepth: 1,
      defaultModelExpandDepth: 1,
      displayRequestDuration: true,
      filter: true,
      tryItOutEnabled: true
    });
    
    // Apply initial theme
    applySwaggerTheme(currentTheme);
    
    // Watch for theme changes
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'data-md-color-scheme') {
          const newTheme = getSwaggerTheme();
          applySwaggerTheme(newTheme);
        }
      });
    });
    
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['data-md-color-scheme']
    });
  };
</script>

<style>
  /* Make Swagger UI use full viewport width */
  .md-content {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  .md-content__inner {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  #swagger-ui {
    width: 100vw !important;
    margin: 0 !important;
    padding: 20px !important;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw !important;
    margin-right: -50vw !important;
  }
  
  /* Hide the title on this page since Swagger UI has its own */
  .md-content h1:first-of-type {
    display: none;
  }
  
  /* Adjust Swagger UI theme to match Material */
  .swagger-ui .topbar {
    display: none;
  }
  
  .swagger-ui .info {
    margin: 20px 0;
  }
  
  /* Light theme styles (default Material theme) */
  [data-md-color-scheme="default"] #swagger-ui {
    background-color: #ffffff !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui {
    background-color: #ffffff !important;
    color: #3b4151 !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock-tag-section {
    background-color: #ffffff !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock-tag {
    background-color: #ffffff !important;
    border-bottom: 1px solid rgba(59, 65, 81, 0.3) !important;
    color: #3b4151 !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock {
    background-color: #ffffff !important;
    border: 1px solid rgba(59, 65, 81, 0.3) !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock .opblock-summary {
    background-color: #fafafa !important;
    border: none !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock .opblock-summary-path {
    color: #3b4151 !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock .opblock-summary-description {
    color: #3b4151 !important;
  }
  
  [data-md-color-scheme="default"] .swagger-ui .opblock-description-wrapper,
  [data-md-color-scheme="default"] .swagger-ui .opblock-body {
    background-color: #ffffff !important;
  }
  
<style>
  .md-content {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  .md-content__inner {
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  #swagger-ui {
    width: 100vw !important;
    margin: 0 !important;
    padding: 20px !important;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw !important;
    margin-right: -50vw !important;
  }
  
  .md-content h1:first-of-type {
    display: none;
  }
  
  .swagger-ui .topbar {
    display: none;
  }
  
  .swagger-ui .info {
    margin: 20px 0;
  }
  
  /* Dark mode - invert everything */
  [data-md-color-scheme="slate"] .swagger-ui {
    filter: invert(0.93) hue-rotate(180deg);
  }
  
  [data-md-color-scheme="slate"] .swagger-ui img {
    filter: invert(1) hue-rotate(180deg);
  }
  
  [data-md-color-scheme="slate"] .swagger-ui .highlight-code {
    filter: invert(1) hue-rotate(180deg);
  }
</style>

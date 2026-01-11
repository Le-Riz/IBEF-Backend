# API Reference (Interactive)

This page displays the complete OpenAPI documentation for the IBEF Backend API.

<div id="redoc-container"></div>

<script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
<script>
  // Load the OpenAPI spec and render ReDoc
  fetch('../assets/openapi.json')
    .then(response => response.json())
    .then(spec => {
      Redoc.init(
        spec,
        {
          scrollYOffset: 50,
          theme: {
            colors: {
              primary: {
                main: '#2196F3'
              }
            },
            typography: {
              fontSize: '15px',
              fontFamily: 'Red Hat Display, sans-serif',
              code: {
                fontFamily: 'JetBrains Mono, monospace'
              }
            }
          }
        },
        document.getElementById('redoc-container')
      );
    });
</script>

<style>
  /* Make ReDoc use full viewport width */
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
  
  #redoc-container {
    width: 100vw !important;
    margin: 0 !important;
    padding: 0 !important;
    position: relative;
    left: 50%;
    right: 50%;
    margin-left: -50vw !important;
    margin-right: -50vw !important;
  }
  
  /* Hide the title on this page since ReDoc has its own */
  .md-content h1:first-of-type {
    display: none;
  }
  
  /* Ensure ReDoc content uses full width */
  #redoc-container > div {
    max-width: 100% !important;
  }
</style>

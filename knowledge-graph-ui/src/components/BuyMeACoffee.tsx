"use client";

import Script from "next/script";

/**
 * Buy Me a Coffee floating widget.
 * Renders the BMC chat-style widget in the bottom-right corner.
 */
export function BuyMeACoffee() {
  return (
    <Script
      id="bmc-widget"
      src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js"
      strategy="lazyOnload"
      data-name="BMC-Widget"
      data-cfasync="false"
      data-id="f9t3zol"
      data-description="Support me on Buy me a coffee!"
      data-message=""
      data-color="#FF813F"
      data-position="Right"
      data-x_margin="18"
      data-y_margin="18"
    />
  );
}

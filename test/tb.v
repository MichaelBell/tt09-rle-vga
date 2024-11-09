`default_nettype none
`timescale 1ns / 1ps

/* This testbench just instantiates the module and makes some convenient wires
   that can be driven / tested by the cocotb test.py.
*/
module tb ();

  // Wire up the inputs and outputs:
  reg clk;
  reg rst_n;
  reg ena;
  reg [7:0] ui_in;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_in;
  wire [7:0] uio_oe;

  wire qspi_sel = ui_in[3];
  wire spi_clk = qspi_sel ? uio_out[1] : uio_out[3];
  wire spi_cs = uio_out[0];
  wire spi_mosi = qspi_sel ? uio_out[2] : uio_out[1];
  wire [3:0] spi_miso;

  reg [3:0] spi_miso_buf [0:5];
  genvar i;
  generate
  for (i = 0; i < 5; i = i + 1) begin
    always @(posedge clk or negedge clk) begin
      spi_miso_buf[i+1] <= spi_miso_buf[i];
    end

    wire [3:0] spi_miso_peek = spi_miso_buf[i];
  end
  endgenerate
  reg [2:0] latency;
  initial latency = 3'd1;

  assign spi_miso = spi_miso_buf[latency];

  assign uio_in = qspi_sel ? {2'b00, spi_miso[3:0], 2'b00} : {2'b00, spi_miso[3:2], 1'b0, spi_miso[1:0], 1'b0};

  wire [5:0] colour = {uo_out[0], uo_out[4], uo_out[1], uo_out[5], uo_out[2], uo_out[6]};
  wire hsync = uo_out[7];
  wire vsync = uo_out[3];
  wire pwm = uio_out[7];

`ifdef GL_TEST
  wire VPWR = 1'b1;
  wire VGND = 1'b0;
`endif  

  // Replace tt_um_example with your module name:
  tt_um_MichaelBell_rle_vga user_project (

      // Include power ports for the Gate Level test:
`ifdef GL_TEST
      .VPWR(VPWR),
      .VGND(VGND),
`endif

      .ui_in  (ui_in),    // Dedicated inputs
      .uo_out (uo_out),   // Dedicated outputs
      .uio_in (uio_in),   // IOs: Input path
      .uio_out(uio_out),  // IOs: Output path
      .uio_oe (uio_oe),   // IOs: Enable path (active high: 0=input, 1=output)
      .ena    (ena),      // enable - goes high when design is selected
      .clk    (clk),      // clock
      .rst_n  (rst_n)     // not reset
  );

endmodule

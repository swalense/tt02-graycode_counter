`default_nettype none
`timescale 1ns/1ps

module simul (
    input xclk,
    input reset,
    input scan_sel,
    input set_clk_div,
    input [8:0] sel,
    input [7:0] user_io_in,
    output slow_clk,
    output [7:0] user_io_out,
    output ready
    );

    initial begin
        $dumpfile ("simul.vcd");
        $dumpvars (0, simul);
        #1;
    end

    wire wbs_stb_i, wbs_cyc_i, wbs_we_i;
    wire [3:0] wbs_sel_i;
    wire [31:0] wbs_dat_i, wbs_adr_i;
    wire [127:0] la_data_in, la_oenb;
    wire [`MPRJ_IO_PADS-1:0] io_in;
    wire user_clock2;
    wire [`MPRJ_IO_PADS-1:0] io_out;
    wire [`MPRJ_IO_PADS-1:0] io_oeb;
    wire wbs_ack_o;
    wire [31:0] wbs_dat_o;
    wire [127:0] la_data_out;
    wire [2:0] user_irq;
    wire [`MPRJ_IO_PADS-10:0] analog_io;

    assign io_in = {user_io_in[7:0], sel[8:0], set_clk_div, 1'b0, 2'b10, 8'b0};

    assign user_io_out = io_out[36:29];
    assign slow_clk = io_out[10];

    wire user_clk = user_io_in[0];
    wire user_rst = user_io_in[1];
    wire user_cs = user_io_in[5];

    user_project_wrapper user_project_wrapper(

        // Wishbone Slave ports (WB MI A)
        .wb_clk_i(xclk),
        .wb_rst_i(reset),

        .wbs_stb_i(wbs_stb_i),
        .wbs_cyc_i(wbs_cyc_i),
        .wbs_we_i(wbs_we_i),
        .wbs_sel_i(wbs_sel_i),
        .wbs_dat_i(wbs_dat_i),
        .wbs_adr_i(wbs_adr_i),

        // Logic Analyzer Signals
        .la_data_in(la_data_in),
        .la_oenb(la_oenb),

        // IOs
        .io_in(io_in),

        // Independent clock (on independent integer divider)
        .user_clock2(user_clock2),

        // IOs
        .io_out(io_out),
        .io_oeb(io_oeb),

        // Wishbone Slave ports (WB MI A)
        .wbs_ack_o(wbs_ack_o),
        .wbs_dat_o(wbs_dat_o),

        // Logic Analyzer Signals
        .la_data_out(la_data_out),

        // User maskable interrupt signals
        .user_irq(user_irq),

        // Analog (direct connection to GPIO pad---use with caution)
        // Note that analog I/O is not available on the 7 lowest-numbered
        // GPIO pads, and so the analog_io indexing is offset from the
        // GPIO indexing by 7 (also upper 2 GPIOs do not have analog_io).
        .analog_io(analog_io)
    );

endmodule

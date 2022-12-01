`default_nettype none
`timescale 1ns/1ps

module tb (
        input clk,
        input rst,
        input [1:0] channels,
        input cs,
        input sck,
        input sdi,
        output [4:0] counter,
        output serial_tx,
        output direction,
        output pwm
    );

    initial begin
        $dumpfile ("tb.vcd");
        $dumpvars (0, tb);
        #1;
    end

    wire [7:0] inputs = {1'b0, sdi, sck, cs, channels[1:0], rst, clk};

    wire [7:0] outputs;
    assign {counter[4:0], direction, pwm, serial_tx} = outputs[7:0];

    swalense_top swalense_top (
        .io_in (inputs),
        .io_out (outputs)
    );

endmodule

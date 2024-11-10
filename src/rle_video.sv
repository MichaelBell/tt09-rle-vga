// SPDX-FileCopyrightText: © 2024 Michael Bell
// SPDX-License-Identifier: Apache-2.0

`default_nettype none

module rle_video (
    input logic clk,
    input logic rstn,

    output logic        read_next,
    output logic        stop_data,
    input  logic        data_ready,
    input  logic [15:0] data,

    input  logic       next_frame,
    input  logic       next_row,
    input  logic       next_pixel,
    output logic [5:0] colour,

    output logic [7:0] pwm_sample
);

    logic [9:0] run_length;
    logic [5:0] low_data;
    logic is_colour;
    logic start;
    logic read_next_r;
    logic [8:0] next_sample_adjust;
    logic [1:0] next_sample_adjust_width;
    logic [1:0] next_sample_adjust_count;
    logic signed [7:0] pwm_adjust;
    logic [7:0] adjusted_pwm_sample;

    assign stop_data = (run_length == 10'h2ff);
    assign read_next = read_next_r && !stop_data;
    assign is_colour = data[15:12] < 4'hB;

    always_ff @(posedge clk) begin
        if (!rstn) begin
            read_next_r <= 0;
            run_length <= 10'h2ff;
            start <= 0;
            colour <= 0;
            low_data <= 0;
            next_sample_adjust_count <= 0;
        end else begin
            read_next_r <= 0;

            if (run_length == 10'h2ff) begin
                run_length <= 1;
                start <= 1;
                colour <= 0;
                low_data <= 0;
                next_sample_adjust_count <= 0;
            end
            else if (start) begin
                if (run_length[0]) begin
                    read_next_r <= 1;
                    run_length[0] <= 0;
                end else if (next_frame && data_ready) begin
                    run_length <= data[15:6];
                    if (is_colour) colour <= data[5:0];
                    else low_data <= data[5:0];
                    read_next_r <= 1;
                    start <= 0;
                end
            end
            else if (next_row && next_sample_adjust_count != 0) begin
                case (next_sample_adjust_width)
                    2'b11: next_sample_adjust <= {next_sample_adjust[5:0], 3'bx};
                    2'b10: next_sample_adjust <= {next_sample_adjust[4:0], 4'bx};
                    default: next_sample_adjust <= 9'bx;
                endcase
                pwm_sample <= adjusted_pwm_sample;
                next_sample_adjust_count <= next_sample_adjust_count - 2'b01;
            end            
            else begin
                if (run_length == 0) begin
                    if (data_ready) begin
                        run_length <= data[15:6];
                        if (is_colour) colour <= data[5:0];
                        else low_data <= data[5:0];
                        read_next_r <= 1;
                    end
                end else if (run_length[9:6] == 4'hC) begin
                    if (next_row) begin
                        run_length <= 0;
                        pwm_sample <= {run_length[1:0], low_data[5:0]};
                        next_sample_adjust_count <= 0;
                    end
                end else if (run_length[9:8] == 2'b11) begin
                    if (next_sample_adjust_count == 0) begin
                        next_sample_adjust_width <= run_length[7:6];
                        next_sample_adjust <= {run_length[5:0], 3'bx};
                        if (next_row) begin
                            run_length <= 0;
                            pwm_sample <= adjusted_pwm_sample;
                            next_sample_adjust_count <= run_length[7:6];
                            case (run_length[7:6])
                                2'b11: next_sample_adjust <= {run_length[2:0], low_data[5:0]};
                                2'b10: next_sample_adjust <= {run_length[1:0], low_data[5:0], 1'bx};
                                2'b01: next_sample_adjust <= {low_data[5:0], 3'bx};
                                default: next_sample_adjust <= 9'bx;
                            endcase
                        end
                    end
                end else if (next_pixel) begin
                    if (run_length == 1 && data_ready) begin
                        run_length <= data[15:6];
                        if (is_colour) colour <= data[5:0];
                        else low_data <= data[5:0];
                        read_next_r <= 1;
                    end
                    else begin
                        run_length <= run_length - 1;
                    end
                end
            end
        end
    end

    always @(*) begin : pwm_calculation
        case (next_sample_adjust_width)
            2'b11: pwm_adjust = {{6{next_sample_adjust[8]}}, next_sample_adjust[7:6]};
            2'b10: pwm_adjust = {{5{next_sample_adjust[8]}}, next_sample_adjust[7:5]};
            2'b01: pwm_adjust = {{3{next_sample_adjust[8]}}, next_sample_adjust[7:3]};
            2'b00: pwm_adjust = 8'bx;
        endcase
    end

    assign adjusted_pwm_sample = pwm_sample + pwm_adjust;

endmodule

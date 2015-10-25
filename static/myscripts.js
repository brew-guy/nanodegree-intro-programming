// This file contains the submission material for the Udacity Nanodegree
// Introduction to Programming by Jes H.

// Here goes my JavaScript for html notes in separate file.

// alert('JS works!');

jQuery.fn.shake = function() {
    this.each(function(i) {
        $(this).css({ "position" : "relative" });
        for (var x = 1; x <= 3; x++) {
            $(this).animate({ left: -10 }, 10).animate({ left: 0 }, 50).animate({ left: 10 }, 10).animate({ left: 0 }, 50);
        }
    });
    return this;
}

$('.lesson').click(function() {
    $(this).shake();
});

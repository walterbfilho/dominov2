$(document).ready(function() {
    $("#accordion").accordion({
        collapsible: true,
        active: false
     });

    $('.players-table').tablesorter({
        sortList: [[0,0]],
        headers: {
            0: { sorter: 'text' } 
        }
    });

    $('.players-table th').click(function() {
        $(this).addClass('blink');
        setTimeout(() => {
            $(this).removeClass('blink'); 
        }, 200);
    });
});
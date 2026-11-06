var query = {
    enviroment: "",
    gender: "",
    disciplineGroup: "",
    disciplineGroup2: ""
}
var filteredJsonDiscipline2;
var filteredJsonDiscipline3;

define(["jquery"], function ($) {

    fillDiscipline();
    $("#byDisciplineDropDown").change(function () {
        fillDiscipline2(this.value);
    });

    $("#byDiscipline2DropDown").change(function () {
        fillDiscipline3(this.value);
    });
    $("#byDiscipline3DropDown").change(function () {
        query.disciplineGroup2 = this.value;
        if (query.disciplineGroup2) {
            redirectDisciplinePage();
        }
    });
    selectDisciplineDropDowns();
    fillDiscipline2($("#byDisciplineDropDown").val());

});

function selectDisciplineDropDowns() {
    const urlArray = window.location.pathname.split("/");
    query.gender = urlArray.pop();
    query.enviroment = urlArray.pop();
    query.disciplineGroup2 = urlArray.pop();
    query.disciplineGroup = urlArray.pop();

 
    $("#byDisciplineDropDown").val(query.gender);

    //$("#byDiscipline3DropDown").val(query.disciplineGroup);

    if ($("#byDisciplineDropDown") !== "") {
        setTimeout(function() {
            $("#byDiscipline2DropDown").val(query.disciplineGroup);
            fillDiscipline3($("#byDiscipline2DropDown").val());

            if ($("#byDiscipline2DropDown") !== "") {
                setTimeout(function () {
                    $("#byDiscipline3DropDown").val(query.disciplineGroup2);

                    $("#diciplineHeader").html($("#byDiscipline3DropDown option:selected").text());
                }, 200);
            }

        }, 100);
    }
 

}

function fillDiscipline() {
    if ($("#jsonDisciplinesHidden").length > 0) {
        var jsonData = JSON.parse($("#jsonDisciplinesHidden").val());

        $.each(jsonData,
            function (i, item) {
                $("#byDisciplineDropDown").append($('<option></option>').val(item.Value).html(item.DisplayText));
            }); 
    }

}

function fillDiscipline2(value) {
    if (typeof value !== 'undefined') {
        query.gender = value

        var jsonData = JSON.parse($("#jsonDisciplinesHidden").val());

        $("#byDiscipline2").show();
        $("#byDiscipline2DropDown").html("");
        $("#byDiscipline3").hide();
        $("#byDiscipline3DropDown").html("");


        filteredJsonDiscipline2 = $(jsonData).filter(function (i, n) {
            return n.Gender === query.gender;
        });

        $("#byDiscipline2DropDown").append($('<option></option>').val("").html("Choose a discipline group"));
        $.each(filteredJsonDiscipline2[0].DisciplineTypes,
            function (i, item) {
                $("#byDiscipline2DropDown").append($('<option></option>').val(item.UrlSlug).html(item.Name));
            });
    }
}

function fillDiscipline3(urlSlug) {
    if (typeof urlSlug !== 'undefined') {
        query.disciplineGroup = urlSlug;

        $("#byDiscipline3").show();
        $("#byDiscipline3DropDown").html("");

        filteredJsonDiscipline3 = $(filteredJsonDiscipline2[0].DisciplineTypes).filter(function(i, n) {
            return n.UrlSlug === urlSlug;
        });

        $("#byDiscipline3DropDown")
            .append($('<option></option>').val("").html("Choose from " + filteredJsonDiscipline3[0].Name));
        $.each(filteredJsonDiscipline3[0].Disciplines,
            function(i, item) {
                $("#byDiscipline3DropDown").append($('<option></option>').val(item.UrlSlug).html(item.Name));
            });
    }
}

function redirectDisciplinePage() {
    var urlString = "/records/by-discipline/" +
        query.disciplineGroup +
        "/" +
        query.disciplineGroup2 +
        "/" +
        query.enviroment +
        "/" +
        query.gender;
    window.location.href = urlString;
}

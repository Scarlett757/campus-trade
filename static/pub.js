function bindUploadPicture() {
    $("#image-upload").on("change", function (event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("picture", file);

         $("#image-placeholder span").text("上传中...");

        $.ajax({  // 替换 $.post 为 $.ajax，更易配置参数（$.post 本质是 ajax 的简化版）
            url: "/upload/picture",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            success: function (result) {
                console.log("上传成功返回：", result);


                let filename = result.filename;
                if (typeof filename === 'string') {
                    filename = filename.trim();
                }

                let imagePreview = $("#image-preview");
                const src = "/media/" + filename;
                console.log("设置预览图片地址：", src);
                imagePreview.attr("src", src);

                // 使用 show/hide 双重保险，确保能见到图片
                imagePreview.removeClass("hidden");
                imagePreview.show();

                $("#image-placeholder").addClass("hidden");
                $("#image-placeholder").hide();

                // 补充：把文件名存入隐藏输入框，提交表单时能传给后端
                $("input[name='picture']").val(filename);

                // $("#category").val(category.id);
                // 完成图片与表单信息的绑定
                $("#picture").val("/media/"+filename);
            },
            error: function (xhr, status, error) {
                // 新增错误提示，方便排查问题
                console.error("上传失败：", error);
                alert("图片上传失败，请重试！");
            }
        });
    });
}

function bindCategoryToggle() {
    const categorySelect = $("#category");
    const newCategoryGroup = $("#new-category-input-group");
    const newCategoryInput = $("#new_category_name");

    categorySelect.on("change", function () {
        if ($(this).val() === "new_category") {
            // 显示输入框
            newCategoryGroup.removeClass("hidden");
            newCategoryInput.prop("required", true); // 必填
            newCategoryInput.focus();
        } else {
            // 隐藏输入框
            newCategoryGroup.addClass("hidden");
            newCategoryInput.prop("required", false);
            newCategoryInput.val(""); // 清空
        }
    });
}


$(function () {
    bindUploadPicture();
    bindCategoryToggle();
});
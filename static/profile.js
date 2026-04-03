// 绑定个人信息更新表单
function bindProfileUpdate() {
    $("#updateForm").on("submit", function(event) {
        event.preventDefault();
        const saveBtn = $("#saveBtn");
        const originalText = saveBtn.html();
        saveBtn.prop("disabled", true).html('<span class="loading-spinner"></span> 保存中...');

        const formData = new FormData(this);

        $.ajax({
            url: "/profile",
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            success: function(resp) {
                alert("个人信息更新成功！");
                location.reload();
            },
            error: function(xhr, status, error) {
                console.error("个人信息更新失败:", error);
                let errorMsg = "更新失败，请重试";
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMsg = xhr.responseJSON.message;
                }
                alert(errorMsg);
                saveBtn.prop("disabled", false).html(originalText);
            }
        });
    });
}

// --- 地址管理相关函数 ---

// 加载地址列表
async function loadAddresses() {
    const listEl = document.getElementById('address-list');
    if (!listEl) return; // 如果元素不存在则不执行

    try {
        console.log("正在请求 /api/address ...");
        const res = await fetch('/api/address');

        // 检查响应状态
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }

        const addresses = await res.json();
        console.log("获取到的地址数据:", addresses);

        if (addresses.length === 0) {
            listEl.innerHTML = '<div class="col-span-full text-center py-8 text-gray-400 bg-gray-50 rounded-lg">暂无收货地址，请点击右上角添加</div>';
            return;
        }

        listEl.innerHTML = '';
        addresses.forEach(addr => {
            const isDefault = addr.is_default;
            const cardClass = isDefault ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500' : 'border-gray-200 bg-white hover:shadow-md';
            const defaultBadge = isDefault ? '<span class="absolute top-2 right-2 bg-emerald-500 text-white text-xs px-2 py-0.5 rounded">默认</span>' : '';

            // 注意：如果地址内容包含单引号，下面的字符串拼接可能会出错，建议用 template literal 或者转义
            // 这里为了简单直接拼接，如果报错请检查地址内容
            const html = `
                <div class="relative p-4 rounded-lg border ${cardClass} transition-all">
                    ${defaultBadge}
                    <div class="flex justify-between items-start mb-2">
                        <div>
                            <span class="font-bold text-gray-800 text-lg">${addr.receiver}</span>
                            <span class="text-gray-600 ml-2">${addr.phone}</span>
                        </div>
                    </div>
                    <p class="text-sm text-gray-600 mb-1">${addr.province}${addr.city}${addr.district}</p>
                    <p class="text-sm text-gray-800 mb-4">${addr.detail}</p>
                    
                    <div class="flex gap-2 border-t border-gray-100 pt-3">
                        ${!isDefault ? `<button onclick="setDefaultAddress(${addr.id})" class="text-xs text-emerald-600 hover:text-emerald-800 font-medium">设为默认</button>` : ''}
                        <button onclick="editAddress(${addr.id}, '${addr.receiver.replace(/'/g, "\\'")}', '${addr.phone}', '${addr.province.replace(/'/g, "\\'")}', '${addr.city.replace(/'/g, "\\'")}', '${addr.district.replace(/'/g, "\\'")}', '${addr.detail.replace(/'/g, "\\'")}', ${addr.is_default})" 
                            class="text-xs text-blue-600 hover:text-blue-800 font-medium">编辑</button>
                        <button onclick="deleteAddress(${addr.id})" class="text-xs text-red-600 hover:text-red-800 font-medium">删除</button>
                    </div>
                </div>
            `;
            listEl.innerHTML += html;
        });
    } catch (e) {
        console.error("加载地址失败详情:", e);
        listEl.innerHTML = `<div class="col-span-full text-center text-red-500">加载地址失败 (${e.message})<br><small>请检查控制台日志或后端路由</small></div>`;
    }
}

// 切换表单显示
function toggleAddressForm(reset = true) {
    const container = document.getElementById('address-form-container');
    const form = document.getElementById('address-form');

    if (!container) return;

    if (container.classList.contains('hidden')) {
        if (reset) {
            form.reset();
            document.getElementById('addr-id').value = '';
            document.getElementById('form-title').innerText = '新增收货地址';
        }
        container.classList.remove('hidden');
    } else {
        container.classList.add('hidden');
    }
}

// 编辑地址填充数据
function editAddress(id, receiver, phone, province, city, district, detail, isDefault) {
    document.getElementById('addr-id').value = id;
    document.getElementById('addr-receiver').value = receiver;
    document.getElementById('addr-phone').value = phone;
    document.getElementById('addr-province').value = province;
    document.getElementById('addr-city').value = city;
    document.getElementById('addr-district').value = district;
    document.getElementById('addr-detail').value = detail;
    document.getElementById('addr-default').checked = isDefault;

    document.getElementById('form-title').innerText = '编辑收货地址';

    const container = document.getElementById('address-form-container');
    container.classList.remove('hidden');
    container.scrollIntoView({ behavior: 'smooth' });
}

// 提交表单 (新增或更新)
async function handleAddressSubmit(e) {
    e.preventDefault();
    const id = document.getElementById('addr-id').value;

    const data = {
        receiver: document.getElementById('addr-receiver').value,
        phone: document.getElementById('addr-phone').value,
        province: document.getElementById('addr-province').value,
        city: document.getElementById('addr-city').value,
        district: document.getElementById('addr-district').value,
        detail: document.getElementById('addr-detail').value,
        is_default: document.getElementById('addr-default').checked
    };

    const url = id ? `/api/address/${id}` : '/api/address';
    const method = id ? 'PUT' : 'POST';

    console.log(`正在${method}请求:`, url, data);

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });

        const result = await res.json();
        console.log("服务器响应:", result);

        if (res.ok && result.success) {
            alert('地址保存成功');
            toggleAddressForm();
            loadAddresses();
        } else {
            alert(result.error || '保存失败');
        }
    } catch (err) {
        console.error("网络错误:", err);
        alert('网络错误，请查看浏览器控制台 (F12)');
    }
}

// 设为默认
async function setDefaultAddress(id) {
    if(!confirm('确定设为默认地址吗？')) return;
    try {
        const res = await fetch(`/api/address/${id}/default`, { method: 'POST' });
        const result = await res.json();
        if (res.ok && result.success) {
            loadAddresses();
        } else {
            alert(result.error || '操作失败');
        }
    } catch (e) {
        alert('网络错误');
    }
}

// 删除地址
async function deleteAddress(id) {
    if(!confirm('确定删除该地址吗？')) return;
    try {
        const res = await fetch(`/api/address/${id}`, { method: 'DELETE' });
        const result = await res.json();
        if (res.ok && result.success) {
            loadAddresses();
        } else {
            alert(result.error || '删除失败');
        }
    } catch (e) {
        alert('网络错误');
    }
}

// 页面加载完成后初始化
$(function() {
    // 1. 绑定个人信息表单
    bindProfileUpdate();

    // 2. 绑定 UI 交互 (编辑/取消按钮)
    const editBtn = $('#editProfileBtn');
    const cancelBtn = $('#cancelEditBtn');
    const profileForm = $('#profileForm');

    editBtn.click(function() {
        profileForm.removeClass('hidden');
        editBtn.addClass('hidden');
    });

    cancelBtn.click(function() {
        profileForm.addClass('hidden');
        editBtn.removeClass('hidden');
        $('#updateForm')[0].reset();
    });

    // 3. 初始化加载地址列表
    // 确保 DOM 中存在 address-list 元素
    if ($('#address-list').length > 0) {
        loadAddresses();
    }
});
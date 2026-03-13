# 算法题库

## problem_001
### 题目：Hello World
### 难度：简单
### 描述
编写一个函数，接收一个名字作为参数，返回 "Hello, {名字}!" 的问候语。

### 示例
```
输入: "World"
输出: "Hello, World!"

输入: "张三"
输出: "Hello, 张三!"
```

### 函数签名
```cpp
#include <iostream>
#include <string>
using namespace std;

string hello(string name) {
    // 在此编写代码

}

int main() {
    // 测试代码
    cout << hello("World") << endl;
    return 0;
}
```

### 参考答案
```cpp
string hello(string name) {
    return "Hello, " + name + "!";
}
```

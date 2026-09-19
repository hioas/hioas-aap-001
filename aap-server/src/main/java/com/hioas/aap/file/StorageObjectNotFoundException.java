package com.hioas.aap.file;

/** 存储对象不存在（映射为 E-1406，不是 500）。 */
public class StorageObjectNotFoundException extends RuntimeException {

    public StorageObjectNotFoundException(String message) {
        super(message);
    }
}

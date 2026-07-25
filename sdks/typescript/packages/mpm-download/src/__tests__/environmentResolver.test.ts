import { test } from "node:test";
import assert from "node:assert/strict";
import { Gs1BeluEnvironmentResolver } from "../environment.js";

test("uat derives the uat hosts and audience", () => {
  assert.equal(Gs1BeluEnvironmentResolver.apiHost("uat"), "api-uat.gs1belu.org");
  assert.equal(Gs1BeluEnvironmentResolver.tokenHost("uat"), "login-uat.gs1belu.org");
  assert.equal(Gs1BeluEnvironmentResolver.audience("uat"), "https://api-uat.gs1belu.org/");
  assert.equal(Gs1BeluEnvironmentResolver.tokenEndpoint("uat"), "https://login-uat.gs1belu.org/oauth/token");
  assert.equal(Gs1BeluEnvironmentResolver.baseUrl("uat", "v17"), "https://api-uat.gs1belu.org/myproductmanager/download/v17");
});

test("prod derives the prod hosts and audience", () => {
  assert.equal(Gs1BeluEnvironmentResolver.apiHost("prod"), "api.gs1belu.org");
  assert.equal(Gs1BeluEnvironmentResolver.tokenHost("prod"), "login.gs1belu.org");
  assert.equal(Gs1BeluEnvironmentResolver.audience("prod"), "https://api.gs1belu.org/");
  assert.equal(Gs1BeluEnvironmentResolver.tokenEndpoint("prod"), "https://login.gs1belu.org/oauth/token");
});

test("audience always carries the mandatory trailing slash", () => {
  assert.ok(Gs1BeluEnvironmentResolver.audience("uat").endsWith("/"));
  assert.ok(Gs1BeluEnvironmentResolver.audience("prod").endsWith("/"));
});

test("baseUrl honors a non-default apiVersion", () => {
  assert.equal(Gs1BeluEnvironmentResolver.baseUrl("prod", "v18"), "https://api.gs1belu.org/myproductmanager/download/v18");
});

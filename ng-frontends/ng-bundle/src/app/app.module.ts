import { BrowserModule } from "@angular/platform-browser";
import { HttpClientModule } from "@angular/common/http";
import { NgModule } from "@angular/core";
import { RouterModule } from "@angular/router";
import { NgbModule } from "@ng-bootstrap/ng-bootstrap";

import { AppComponent } from "./app.component";
import { APP_ROUTES } from "./app.routes";
import { ServerLogComponent } from "./server-log/server-log.component";
import { BundleListComponent } from "./bundle-list/bundle-list.component";
import { SelectFilterComponent } from "./select-filter/select-filter.component";
import { BundleEditComponent } from "./bundle-edit/bundle-edit.component";
import { MockBundleListService } from "./test/mock-bundle-list-service.class";
import { BundleListService } from "./bundle-list/bundle-list.service";

@NgModule({
  declarations: [
    AppComponent,
    ServerLogComponent,
    BundleListComponent,
    SelectFilterComponent,
    BundleEditComponent
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    NgbModule,
    RouterModule.forRoot(APP_ROUTES)
  ],
  //providers: [{ provide: BundleListService, useClass: MockBundleListService }],
  bootstrap: [AppComponent]
})
export class AppModule {}

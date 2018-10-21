import { Injectable } from '@angular/core';
import { Observer, Observable } from 'rxjs';
import { IBundleListItem } from '../shared/bundle-list-item.interface';
import { HttpClient } from '@angular/common/http';

@Injectable({
  providedIn: 'root'
})
export class BundleListService {
  observer: Observer<IBundleListItem[]>;

  constructor(private http: HttpClient) { }

  getBundleList(): Observable<IBundleListItem[]> {
    return this.http.get<IBundleListItem[]>("/bundleList");
  }
}
